import os, sys
from django.shortcuts import render, get_object_or_404, HttpResponse
from django.template.context_processors import csrf
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q
from django.db import connection
import lasair.settings
from lasair.models import Objects, Comments
from lasair.models import Myqueries
from lasair.models import Watchlists
import mysql.connector
import ephem, math
from datetime import datetime, timedelta
import json
from utility.mag import dc_mag
from utility.objectStore import objectStore

# 2020-08-03 KWS Added cassandra connectivity
from cassandra.cluster import Cluster
from cassandra.query import dict_factory

def connect_db():
    msl = mysql.connector.connect(
        user    =lasair.settings.READONLY_USER,
        password=lasair.settings.READONLY_PASS,
        host    =lasair.settings.DATABASES['default']['HOST'],
        database='lasair')
    return msl

def ecliptic(ra, dec):
    np = ephem.Equatorial(math.radians(ra), math.radians(dec), epoch='2000')
    e = ephem.Ecliptic(np)
    return (math.degrees(e.lon), math.degrees(e.lat))

def rasex(ra):
    h = math.floor(ra/15)
    ra -= h*15
    m = math.floor(ra*4)
    ra -= m/4.0
    s = ra*240
    return '%02d:%02d:%.3f' % (h, m, s)

def decsex(de):
    ade = abs(de)
    d = math.floor(ade)
    ade -= d
    m = math.floor(ade*60)
    ade -= m/60.0
    s = ade*3600
    if de > 0.0:
        return '%02d:%02d:%.3f' % (d, m, s)
    else:
        return '-%02d:%02d:%.3f' % (d, m, s)

def objhtml(request, objectId):
    data = obj(request, objectId)
    data2 = data.copy()
    if 'comments' in data2:
        data2.pop('comments')
    return render(request, 'show_object.html',
        {'data':data, 'json_data':json.dumps(data2),
        'authenticated': request.user.is_authenticated})

def objjson(request, objectId):
    data = obj(request, objectId)
    if 'comments' in data:
        data.pop('comments')
    return HttpResponse(json.dumps(data, indent=2), content_type="application/json")

def obj(request, objectId):
    """Show a specific object, with all its candidates"""
    objectData = None
    message = ''
    msl = connect_db()
    cursor = msl.cursor(buffered=True, dictionary=True)
    query = 'SELECT ncand, ramean, decmean, glonmean, glatmean '
    query += 'FROM objects WHERE objectId = "%s"' % objectId
    cursor.execute(query)
    for row in cursor:
        objectData = row

    comments = []
    if objectData:
        qcomments = Comments.objects.filter(objectid=objectId).order_by('-time')
        for c in qcomments: 
            comments.append(
                {'name':c.user.first_name+' '+c.user.last_name,
                 'content': c.content,
                 'time': c.time,
                 'comment_id': c.comment_id,
                 'mine': (c.user == request.user)})
        message += ' and %d comments' % len(comments)
        message += str(comments)

#    crossmatches = []
    if objectData:
        if objectData and 'annotation' in objectData and objectData['annotation']:
            objectData['annotation'] = objectData['annotation'].replace('"', '').strip()

        objectData['rasex'] = rasex(objectData['ramean'])
        objectData['decsex'] = decsex(objectData['decmean'])

        (ec_lon, ec_lat) = ecliptic(objectData['ramean'], objectData['decmean'])
        objectData['ec_lon'] = ec_lon
        objectData['ec_lat'] = ec_lat

#        query = 'SELECT catalogue_object_id, catalogue_table_name, catalogue_object_type, separationArcsec, '
#        query += '_r AS r, _g AS g, photoZ, rank '
#        query += 'FROM sherlock_crossmatches where objectId="%s"' % objectId
#        query += 'ORDER BY -rank DESC'
#        cursor.execute(query)
#        for row in cursor:
#            if row['rank']:
#                crossmatches.append(row)
#    message += ' and %d crossmatches' % len(crossmatches)

    sherlock = {}
    query = 'SELECT * from sherlock_classifications WHERE objectId = "%s"' % objectId
    cursor.execute(query)
    for row in cursor:
        sherlock = row
    #message += str(sherlock)   #%%%%%%%



    if lasair.settings.CASSANDRA is not None:

        # 2020-08-03 KWS Get lightcurve from Cassandra.  By default Django connects to MySQL.  But we'd also
        #                like to get our lightcurves from Cassandra.  Don't connect to Cassandra here - massive
        #                overhead.  Place settings in settings.py and connect a session at startup.  This is
        #                a quick and dirty fix.  Try passing the session to this method.

        cluster = Cluster()
        session = cluster.connect()

        # Set the row_factory to dict_factory to simulate what Roy is doing below! Otherwise
        # the data returned will be in the form of object properties.
        session.row_factory = dict_factory

        session.set_keyspace(lasair.settings.CASSANDRA['default']['KEYSPACE'])

        #noncands = session.execute("""SELECT * from prv_candidates where objectId = %s""", (objectId,) )
        candidates = []
        candlist = session.execute("""SELECT * from candidates where objectId = %s""", (objectId,) )

        count_isdiffpos = count_real_candidates = 0

        for cand in candlist:
            row = {}
            for key in ['candid', 'jd', 'ra', 'dec', 'fid', 'nid', 'magpsf', 'sigmapsf', 'isdiffpos', 
                    'ssdistnr', 'ssnamenr', 'drb']:
                if key in cand:
                    row[key] = cand[key]
            row['mjd'] = mjd = float(cand['jd']) - 2400000.5
            date = datetime.strptime("1858/11/17", "%Y/%m/%d")
            date += timedelta(mjd)
            row['utc'] = date.strftime("%Y-%m-%d %H:%M:%S")
            ssnamenr = cand['ssnamenr']
            if ssnamenr == 'null':
                ssnamenr = None
            if cand['candid'] and cand['isdiffpos'] == 'f':
                count_isdiffpos += 1
            if not cand['candid']:
                row['magpsf'] = cand['diffmaglim']
            candidates.append(row)

        # Disconnect from Cassandra.
        cluster.shutdown()

    else:



        lightcurves = objectStore(suffix = 'json',
            fileroot=lasair.settings.BLOB_STORE_ROOT + '/lightcurve/')

#        try:
        alertjson = lightcurves.getObject(objectId)
#        except:
#            message = 'objectId %s does not exist'%objectId
#            data = {'objectId':objectId, 'message':message}
#            return data

        alert = json.loads(alertjson)
        candidates = []
 
#        query = 'SELECT candid, jd-2400000.5 as mjd, ra, decl, fid, nid, magpsf,sigmapsf, '
#        query += 'magnr,sigmagnr, magzpsci, isdiffpos, ssdistnr, ssnamenr, ndethist, '
#        query += 'dc_mag, dc_sigmag,dc_mag_g02,dc_mag_g08,dc_mag_g28,dc_mag_r02,dc_mag_r08,dc_mag_r28, '
#        query += 'drb '
#        query += 'FROM candidates WHERE objectId = "%s" ' % objectId
#        cursor.execute(query)
        count_isdiffpos = count_real_candidates = 0

        candlist = alert['prv_candidates'] + [alert['candidate']]
        candidates = []
        for cand in candlist:
            row = {}
            for key in ['candid', 'jd', 'ra', 'dec', 'fid', 'nid', 'magpsf', 'sigmapsf', 'isdiffpos', 
                    'ssdistnr', 'ssnamenr', 'drb']:
                if key in cand:
                    row[key] = cand[key]
            row['mjd'] = mjd = float(cand['jd']) - 2400000.5
            date = datetime.strptime("1858/11/17", "%Y/%m/%d")
            date += timedelta(mjd)
            row['utc'] = date.strftime("%Y-%m-%d %H:%M:%S")
            ssnamenr = cand['ssnamenr']
            if ssnamenr == 'null':
                ssnamenr = None
            if cand['candid'] and cand['isdiffpos'] == 'f':
                count_isdiffpos += 1
            if not cand['candid']:
                row['magpsf'] = cand['diffmaglim']
            candidates.append(row)









    if not objectData:
        ra = float(cand['ra'])
        dec = float(cand['dec'])
        objectData = {'ramean': ra, 'decmean': dec, 
            'rasex': rasex(ra), 'decsex': decsex(dec),
            'ncand':len(candidates), 'MPCname':ssnamenr}
        objectData['annotation'] = 'Unknown object'
        if row['ssdistnr'] > 0 and row['ssdistnr'] < 10:
            objectData['MPCname'] = ssnamenr

    #message += 'Got %d candidates' % len(candlist)


#    query = 'SELECT jd-2400000.5 as mjd, fid, diffmaglim '
#    query += 'FROM noncandidates WHERE objectId = "%s"' % objectId
#    cursor.execute(query)
#    for cand in candlist:
#        mjd = float(row['mjd'])
#        date = datetime.strptime("1858/11/17", "%Y/%m/%d")
#        date += timedelta(mjd)
#        row['utc'] = date.strftime("%Y-%m-%d %H:%M:%S")
#        row['magpsf'] = row['diffmaglim']
#        candidates.append(row)
    message += 'Got %d candidates and noncandidates' % len(candidates)

    candidates.sort(key= lambda c: c['mjd'], reverse=True)

    data = {'objectId':objectId, 'objectData': objectData, 'candidates': candidates, 
        'count_isdiffpos': count_isdiffpos, 'count_real_candidates':count_real_candidates,
        'sherlock': sherlock, 'message':message,
        'comments':comments}
    return data

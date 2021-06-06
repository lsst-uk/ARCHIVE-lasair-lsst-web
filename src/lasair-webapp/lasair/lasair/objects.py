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
import time
#import fastavro

# 2020-08-03 KWS Added cassandra connectivity
if lasair.settings.CASSANDRA_HEAD is not None:
    from cassandra.cluster import Cluster
    from cassandra.query import dict_factory

def connect_db():
    """connect_db.
    """
    msl = mysql.connector.connect(
        user    =lasair.settings.READONLY_USER,
        password=lasair.settings.READONLY_PASS,
        host    =lasair.settings.DATABASES['default']['HOST'],
        database='ztf')
    return msl

def mjd_now():
    return time.time()/86400 + 40587.0

def ecliptic(ra, dec):
    """ecliptic.

    Args:
        ra:
        dec:
    """
    np = ephem.Equatorial(math.radians(ra), math.radians(dec), epoch='2000')
    e = ephem.Ecliptic(np)
    return (math.degrees(e.lon), math.degrees(e.lat))

def rasex(ra):
    """rasex.

    Args:
        ra:
    """
    h = math.floor(ra/15)
    ra -= h*15
    m = math.floor(ra*4)
    ra -= m/4.0
    s = ra*240
    return '%02d:%02d:%.3f' % (h, m, s)

def decsex(de):
    """decsex.

    Args:
        de:
    """
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
    """objhtml.

    Args:
        request:
        objectId:
    """
    data = obj(objectId)
    if not data:
        return render(request, 'error.html', 
                {'message': 'Object %s not in database' % objectId})

    data2 = data.copy()
    if 'sherlock' in data2:
        data2.pop('sherlock')
    return render(request, 'show_object.html',
        {'data':data, 'json_data':json.dumps(data2),
        'authenticated': request.user.is_authenticated})

def objjson(objectId):
    """objjson.

    Args:
        request:
        objectId:
    """
    data = obj(objectId)
    return data

def obj(objectId):
    """Show a specific object, with all its candidates"""
    objectData = None
    message = ''
    msl = connect_db()
    cursor = msl.cursor(buffered=True, dictionary=True)
    query = 'SELECT ncand, ramean, decmean, glonmean, glatmean, jdmin, jdmax '
    query += 'FROM objects WHERE objectId = "%s"' % objectId
    cursor.execute(query)
    for row in cursor:
        objectData = row

#    comments = []
#    if objectData:
#        qcomments = Comments.objects.filter(objectid=objectId).order_by('-time')
#        for c in qcomments: 
#            comments.append(
#                {'name':c.user.first_name+' '+c.user.last_name,
#                 'content': c.content,
#                 'time': c.time,
#                 'comment_id': c.comment_id,
#                 'mine': (c.user == request_user)})
#        message += ' and %d comments' % len(comments)
#        message += str(comments)
#    else:
#        return None

#    crossmatches = []
    if objectData:
        if objectData and 'annotation' in objectData and objectData['annotation']:
            objectData['annotation'] = objectData['annotation'].replace('"', '').strip()

        objectData['rasex'] = rasex(objectData['ramean'])
        objectData['decsex'] = decsex(objectData['decmean'])

        (ec_lon, ec_lat) = ecliptic(objectData['ramean'], objectData['decmean'])
        objectData['ec_lon'] = ec_lon
        objectData['ec_lat'] = ec_lat

        now = mjd_now()
        objectData['now_mjd'] = '%.2f' % now
        objectData['mjdmin_ago'] = now - (objectData['jdmin'] - 2400000.5)
        objectData['mjdmax_ago'] = now - (objectData['jdmax'] - 2400000.5)

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

    TNS = {}
    query = 'SELECT tns_name, tns_prefix, disc_mag, type, z, host_name, associated_groups '
    query += 'FROM crossmatch_tns JOIN watchlist_hits ON crossmatch_tns.tns_name = watchlist_hits.name '
    query += 'WHERE watchlist_hits.wl_id=%d AND watchlist_hits.objectId="%s"' % (lasair.settings.TNS_WATCHLIST_ID, objectId)

    cursor.execute(query)
    for row in cursor:
        for k,v in row.items():
            if v: TNS[k] = v
    #message += str(TNS)   #%%%%%%%


    if lasair.settings.CASSANDRA_HEAD is not None:

        # 2020-08-03 KWS Get lightcurve from Cassandra.  By default Django connects to MySQL.  But we'd also
        #                like to get our lightcurves from Cassandra.  Don't connect to Cassandra here - massive
        #                overhead.  Place settings in settings.py and connect a session at startup.  This is
        #                a quick and dirty fix.  Try passing the session to this method.

        cluster = Cluster(lasair.settings.CASSANDRA_HEAD)
        session = cluster.connect()

        # Set the row_factory to dict_factory to simulate what Roy is doing below! Otherwise
        # the data returned will be in the form of object properties.
        session.row_factory = dict_factory

        session.set_keyspace('lasair')

        #noncands = session.execute("""SELECT * from prv_candidates where objectId = %s""", (objectId,) )
        candidates = []
        candlist = session.execute("""SELECT * from candidates where objectId = %s""", (objectId,) )

        count_isdiffpos = count_all_candidates = 0

        for cand in candlist:
            row = {}
            for key in ['candid', 'jd', 'ra', 'dec', 'fid', 'nid', 'magpsf', 'sigmapsf', 'isdiffpos', 
                    'ssdistnr', 'ssnamenr', 'drb']:
                if key in cand:
                    row[key] = cand[key]
            row['mjd'] = mjd = float(cand['jd']) - 2400000.5
            row['since_now'] = mjd - now;
            date = datetime.strptime("1858/11/17", "%Y/%m/%d")
            date += timedelta(mjd)
            row['utc'] = date.strftime("%Y-%m-%d %H:%M:%S")
            ssnamenr = cand['ssnamenr']
            if ssnamenr == 'null':
                ssnamenr = None
            count_all_candidates += 1
            if cand['candid'] and (cand['isdiffpos'] == 'f' or cand['isdiffpos'] == '0'):
                count_isdiffpos += 1
            if not cand['candid']:
                row['magpsf'] = cand['diffmaglim']
            candidates.append(row)

        # Disconnect from Cassandra.
        cluster.shutdown()

    else:



        json_store = objectStore(suffix = 'json',
            fileroot=lasair.settings.BLOB_STORE_ROOT + '/objectjson')

        json_object = json_store.getObject(objectId)

        if not json_object:
            message = 'objectId %s does not exist'%objectId
            data = {'objectId':objectId, 'message':message}
            return data

        alert = json.loads(json_object)
        candidates = []
 
        count_isdiffpos = count_all_candidates = 0

#        if 'prv_candidates' in alert and alert['prv_candidates']:
#            candlist = alert['prv_candidates'] + [alert['candidate']]
#        else:
#            candlist = [alert['candidate']]
        candlist = alert['candidates']
 
        candidates = []
        for cand in candlist:
            row = {}
#            if not 'candid' in cand or not cand['candid']:   # nondetections
#                continue

            candid = cand['candid']
            for key in ['candid', 'jd', 'ra', 'dec', 'fid', 'nid', 'magpsf', 'sigmapsf', 'isdiffpos', 
                    'ssdistnr', 'ssnamenr', 'drb']:
                if key in cand:
                    row[key] = cand[key]
            row['mjd'] = mjd = float(cand['jd']) - 2400000.5
            row['since_now'] = mjd - now;
            date = datetime.strptime("1858/11/17", "%Y/%m/%d")
            date += timedelta(mjd)
            row['utc'] = date.strftime("%Y-%m-%d %H:%M:%S")
            if 'ssnamenr' in cand:
                ssnamenr = cand['ssnamenr']
                if ssnamenr == 'null':
                    ssnamenr = None
            count_all_candidates += 1
            if candid and (cand['isdiffpos'] == 'f' or cand['isdiffpos'] == '0'):
                count_isdiffpos += 1
            if not candid:
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

    message += 'Got %d candidates and noncandidates' % len(candidates)

    candidates.sort(key= lambda c: c['mjd'], reverse=True)

    data = {'objectId':objectId, 
            'objectData': objectData, 
            'candidates': candidates, 
            'count_isdiffpos': count_isdiffpos, 
            'count_all_candidates':count_all_candidates,
            'sherlock': sherlock, 
            'TNS':TNS, 'message':message,
            }
    return data

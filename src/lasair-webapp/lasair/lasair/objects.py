import os, sys
from django.shortcuts import render, get_object_or_404, HttpResponse
from django.template.context_processors import csrf
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q
from django.db import connection
import lasair.settings
from lasair.models import Myqueries
from lasair.models import Watchlists
import mysql.connector
import ephem, math
from datetime import datetime, timedelta
import json
from utility.mag import dc_mag
from utility.objectStore import objectStore
import time
from lasair.lightcurves import lightcurve_fetcher

def connect_db():
    """connect_db.
    """
    msl = mysql.connector.connect(
        user    =lasair.settings.READONLY_USER,
        password=lasair.settings.READONLY_PASS,
        host    =lasair.settings.DATABASES['default']['HOST'],
        port    = lasair.settings.DATABASES['default']['PORT'],
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

    if not objectData:
        return None

    now = mjd_now()
    if objectData:
        if objectData and 'annotation' in objectData and objectData['annotation']:
            objectData['annotation'] = objectData['annotation'].replace('"', '').strip()

        objectData['rasex'] = rasex(objectData['ramean'])
        objectData['decsex'] = decsex(objectData['decmean'])

        (ec_lon, ec_lat) = ecliptic(objectData['ramean'], objectData['decmean'])
        objectData['ec_lon'] = ec_lon
        objectData['ec_lat'] = ec_lat

        objectData['now_mjd'] = '%.2f' % now
        objectData['mjdmin_ago'] = now - (objectData['jdmin'] - 2400000.5)
        objectData['mjdmax_ago'] = now - (objectData['jdmax'] - 2400000.5)

    sherlock = {}
    query = 'SELECT * from sherlock_classifications WHERE objectId = "%s"' % objectId
    cursor.execute(query)
    for row in cursor:
        sherlock = row

    TNS = {}
    query = 'SELECT tns_name, tns_prefix, disc_mag, type, z, host_name, source_group '
    query += 'FROM crossmatch_tns JOIN watchlist_hits ON crossmatch_tns.tns_name = watchlist_hits.name '
    query += 'WHERE watchlist_hits.wl_id=%d AND watchlist_hits.objectId="%s"' % (lasair.settings.TNS_WATCHLIST_ID, objectId)

    cursor.execute(query)
    for row in cursor:
        for k,v in row.items():
            if v: TNS[k] = v

    # Fetch the lightcurve, either from cassandra or file system
    if lasair.settings.CASSANDRA_HEAD is not None:
        LF = lightcurve_fetcher(cassandra_hosts=lasair.settings.CASSANDRA_HEAD)
    else:
        LF = lightcurve_fetcher(fileroot=lasair.settings.BLOB_STORE_ROOT+'/objectjson')

    candidates = LF.fetch(objectId)
    LF.close()

    count_isdiffpos = count_all_candidates = count_noncandidate = 0
    for cand in candidates:
        cand['mjd'] = mjd = float(cand['jd']) - 2400000.5
        cand['since_now'] = mjd - now;
        if 'candid' in cand:
            count_all_candidates += 1
            candid = cand['candid']
            date = datetime.strptime("1858/11/17", "%Y/%m/%d")
            date += timedelta(mjd)
            cand['utc'] = date.strftime("%Y-%m-%d %H:%M:%S")
            if 'ssnamenr' in cand:
                ssnamenr = cand['ssnamenr']
                if ssnamenr == 'null':
                    ssnamenr = None
            if cand['isdiffpos'] == 'f' or cand['isdiffpos'] == '0':
                count_isdiffpos += 1
        else:
            count_noncandidate += 1
            cand['magpsf'] = cand['diffmaglim']

    if count_all_candidates == 0:
        return None

    if not objectData:
        ra = float(cand['ra'])
        dec = float(cand['dec'])
        objectData = {'ramean': ra, 'decmean': dec, 
            'rasex': rasex(ra), 'decsex': decsex(dec),
            'ncand':len(candidates), 'MPCname':ssnamenr}
        objectData['annotation'] = 'Unknown object'
        if row['ssdistnr'] > 0 and row['ssdistnr'] < 10:
            objectData['MPCname'] = ssnamenr

    message += 'Got %d candidates and %d noncandidates' % (count_all_candidates, count_noncandidate)

    candidates.sort(key= lambda c: c['mjd'], reverse=True)

    data = {'objectId':objectId, 
            'objectData': objectData, 
            'candidates': candidates, 
            'count_isdiffpos': count_isdiffpos, 
            'count_all_candidates':count_all_candidates,
            'count_noncandidate':count_noncandidate,
            'sherlock': sherlock, 
            'TNS':TNS, 'message':message,
            }
    return data

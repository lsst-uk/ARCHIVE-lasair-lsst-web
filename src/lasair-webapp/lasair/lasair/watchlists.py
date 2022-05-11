from django.shortcuts import render, get_object_or_404
from django.template.context_processors import csrf
from django.views.decorators.csrf import csrf_exempt
from django.db import connection
from django.contrib.auth.models import User
from django.http import HttpResponse
import lasair.settings
from lasair.models import Watchlists, WatchlistCones
import mysql.connector
import json
import random
from subprocess import Popen, PIPE
import time

def connect_db(write=False):
    """connect_db.
    """
    if write:
        msl = mysql.connector.connect(
        user    =lasair.settings.READWRITE_USER,
        password=lasair.settings.READWRITE_PASS,
        host    =lasair.settings.DATABASES['default']['HOST'],
        port    =lasair.settings.DATABASES['default']['PORT'],
        database='ztf')
    else:
        msl = mysql.connector.connect(
        user    =lasair.settings.READONLY_USER,
        password=lasair.settings.READONLY_PASS,
        host    =lasair.settings.DATABASES['default']['HOST'],
        port    =lasair.settings.DATABASES['default']['PORT'],
        database='ztf')

    return msl

def handle_uploaded_file(f):
    """handle_uploaded_file.

    Args:
        f:
    """
    return f.read().decode('utf-8')

def watchlist_new(request):
    return render(request, 'watchlist_new.html',
        {'random': '%d'%random.randrange(1000),
        'authenticated': request.user.is_authenticated
        })

def get_numbers(watchlists):
    for wl in watchlists:
        wl['number'] = WatchlistCones.objects.filter(wl_id=wl['wl_id']).count()
    return watchlists

@csrf_exempt
def watchlists_home(request):
    """watchlists_home.

    Args:
        request:
    """
    message = ''
    if request.method == 'POST' and request.user.is_authenticated:
        delete      = request.POST.get('delete')

        if delete == None:   # create new watchlist

            t = time.time()
            name           = request.POST.get('name')
            description    = request.POST.get('description')
            d_radius       = request.POST.get('radius')

            cones          = request.POST.get('cones_textarea')
            if 'cones_file' in request.FILES:
                cones     = handle_uploaded_file(request.FILES['cones_file'])

            try:
                default_radius      = float(d_radius)
            except:
                message += 'Cannot parse default radius %s\n' % d_radius

            cone_list = []
            for line in cones.split('\n'):
                if len(line) == 0: continue
                if line[0] == '#': continue
                line = line.replace('|', ',')
                tok = line.split(',')
                if len(tok) < 2: continue
                try:
                    if len(tok) >= 3:
                        ra       = float(tok[0])
                        dec      = float(tok[1])
                        objectId = tok[2].strip()
                        if len(tok) >= 4: radius = float(tok[3])
                        else:             radius = None
                        cone_list.append([objectId, ra, dec, radius])
                except Exception as e:
                    message += "Bad line %d: %s<br/>" % (len(cone_list), line)
                    message += str(e)
            wl = Watchlists(user=request.user, name=name, description=description, active=0, radius=default_radius)
            wl.save()
            cones = []
            for cone in cone_list:
                name = cone[0].encode('ascii', 'ignore').decode()
                if name != cone[0]:
                    message += 'Non-ascii characters removed from name %s --> %s<br/>' % (cone[0], name)
                wlc = WatchlistCones(wl=wl, name=name, ra=cone[1], decl=cone[2], radius=cone[3])
                cones.append(wlc)
            chunks = 1 + int(len(cones)/50000)
            for i in range(chunks):
                WatchlistCones.objects.bulk_create(cones[(i*50000) : ((i+1)*50000)])
#            wlc.save()
            message += 'Watchlist created successfully with %d sources in %d chunks in %.1f sec' % (len(cone_list), chunks, time.time()-t)
        else:
            wl_id = int(delete)
            watchlist = get_object_or_404(Watchlists, wl_id=wl_id)
            if request.user == watchlist.user:
                # delete all the cones of this watchlist
                WatchlistCones.objects.filter(wl_id=wl_id).delete()
                # delete all the hits of this watchlist
                query = 'DELETE from watchlist_hits WHERE wl_id=%d' % wl_id
                msl = connect_db(write=True)
                cursor = msl.cursor(buffered=True, dictionary=True)
                cursor.execute(query)
                msl.commit()
                # delete the watchlist
                watchlist.delete()
                message = 'Watchlist %s deleted successfully' % watchlist.name
            else:
                message = 'Must be owner to delete watchlist'

# public watchlists belong to the anonymous user
    other_watchlists = Watchlists.objects.filter(public=1).values()
    other_watchlists = get_numbers(other_watchlists)

    if request.user.is_authenticated:
        my_watchlists    = Watchlists.objects.filter(user=request.user).values()
        my_watchlists = get_numbers(my_watchlists)
    else:
        my_watchlists    = None

    return render(request, 'watchlists_home.html',
        {'my_watchlists': my_watchlists, 
            'random': '%d'%random.randrange(1000),
        'other_watchlists': other_watchlists, 
        'authenticated': request.user.is_authenticated,
        'message': message})

def show_watchlist_txt(request, wl_id):
    """show_watchlist_txt.

    Args:
        request:
        wl_id:
    """
    message = ''
    watchlist = get_object_or_404(Watchlists, wl_id=wl_id)

    is_owner = (request.user.is_authenticated) and (request.user == watchlist.user)
    is_public = (watchlist.public == 1)
    is_visible = is_owner or is_public
    if not is_visible:
        return render(request, 'error.html',{
            'message': "This watchlist is private and not visible to you"})
    cursor = connection.cursor()
    s = []
    cursor.execute('SELECT ra, decl, name, radius FROM watchlist_cones WHERE wl_id=%d LIMIT 10000' % wl_id)
    cones = cursor.fetchall()
    for c in cones:
        if c[3]:
            s += '%f, %f, %s, %f\n' % (c[0], c[1], c[2], c[3])
        else:
            s += '%f, %f, %s\n' % (c[0], c[1], c[2])
    return HttpResponse(s, content_type="text/plain")

def show_watchlist(request, wl_id):
    """show_watchlist.

    Args:
        request:
        wl_id:
    """
    message = ''
    watchlist = get_object_or_404(Watchlists, wl_id=wl_id)

    is_owner = (request.user.is_authenticated) and (request.user == watchlist.user)
    is_public = (watchlist.public == 1)
    is_visible = is_owner or is_public
    if not is_visible:
        return render(request, 'error.html',{
            'message': "This watchlist is private and not visible to you"})

    if request.method == 'POST' and is_owner:
        if 'name' in request.POST:
            watchlist.name        = request.POST.get('name')
            watchlist.description = request.POST.get('description')

            if request.POST.get('active'): watchlist.active  = 1
            else:                          watchlist.active  = 0

            if request.POST.get('public'): watchlist.public  = 1
            else:                          watchlist.public  = 0

            watchlist.radius      = float(request.POST.get('radius'))
            if watchlist.radius > 360: watchlist.radius = 360
            watchlist.save()
            message += 'watchlist updated'
        else:
            from lasair.run_crossmatch import run_watchlist
            hits = run_watchlist(wl_id)
            message += '%d crossmatches found' % hits

    cursor = connection.cursor()
    cursor.execute('SELECT count(*) AS count FROM watchlist_cones WHERE wl_id=%d' % wl_id)
    for row in cursor:
        number_cones = row[0]

#    query = """
#SELECT 
#c.ra, c.decl, c.name, c.radius, o.objectId, o.ncand, h.arcsec,
#o.gmag-o.maggmean AS gdiff, o.rmag-o.magrmean AS rdiff, s.classification
#FROM watchlist_cones AS c 
#LEFT JOIN watchlist_hits           AS h ON c.cone_id = h.cone_id 
#LEFT JOIN objects                  AS o on h.objectId = o.objectId 
#LEFT JOIN sherlock_classifications AS s on o.objectId = s.objectId
#WHERE c.wl_id=%d ORDER BY o.ncand DESC LIMIT 100
#"""
#    query = """
#SELECT 
#c.ra, c.decl, c.name, c.radius, o.objectId, o.ncand, h.arcsec
#FROM watchlist_cones AS c 
#LEFT JOIN watchlist_hits           AS h ON c.cone_id = h.cone_id 
#LEFT JOIN objects                  AS o on h.objectId = o.objectId 
#WHERE c.wl_id=%d ORDER BY o.ncand DESC LIMIT 100
#"""


    query_hit = """
SELECT 
c.ra, c.decl, c.name, c.radius, c.cone_id, o.objectId, o.ncand, jdnow()-o.jdmax, h.arcsec
FROM watchlist_cones AS c 
NATURAL JOIN watchlist_hits as h
NATURAL JOIN objects AS o
WHERE c.wl_id=%d ORDER BY o.jdmax DESC
"""
    query_nohit = """
SELECT 
c.ra, c.decl, c.name, c.radius, c.cone_id
FROM watchlist_cones AS c 
WHERE c.wl_id=%d LIMIT 100
"""
    cursor.execute(query_hit % wl_id)
    hits = cursor.fetchall()
    conelist = []
    coneIdList = []
    number_hits = len(hits)
    number_in_list = 0

    for c in hits:
        d = {'ra'  :c[0], 'decl' :c[1], 'name':c[2]}
        if c[3]: d['radius'] = c[3]
        else:    d['radius'] = watchlist.radius
        coneId = c[4]
        d['objectId'] = c[5]
        d['ncand']    = c[6]
        d['age']      = c[7]
        d['arcsec']   = c[8]
        coneIdList.append(coneId)
        conelist.append(d)
        number_in_list += 1
        if number_in_list >= 100: break

    cursor.execute(query_nohit % wl_id)
    cones = cursor.fetchall()
    for c in cones:
        d = {'ra'  :c[0], 'decl' :c[1], 'name':c[2]}
        if c[3]: d['radius'] = c[3]
        else:    d['radius'] = watchlist.radius
        coneId = c[4]
        if coneId not in coneIdList:
            number_in_list += 1
            if number_in_list >= 100: break
            conelist.append(d)

    count = len(conelist)
    
    return render(request, 'show_watchlist.html',{
        'watchlist':watchlist, 
        'conelist' :conelist, 
        'count'    : len(conelist), 
        'number_cones': number_cones,
        'number_hits' : number_hits,
        'is_owner' :is_owner,
        'message'  :message})

from django.shortcuts import render, get_object_or_404
from django.template.context_processors import csrf
from django.views.decorators.csrf import csrf_exempt
from django.db import connection
from django.contrib.auth.models import User
from django.http import HttpResponse
import lasair.settings
from lasair.models import Watchlists, WatchlistCones, WatchlistHits
import mysql.connector
import json
import random
from subprocess import Popen, PIPE
import time

def connect_db():
    """connect_db.
    """
    msl = mysql.connector.connect(
        user    =lasair.settings.READONLY_USER,
        password=lasair.settings.READONLY_PASS,
        host    =lasair.settings.DATABASES['default']['HOST'],
        database='ztf')
    return msl

def handle_uploaded_file(f):
    """handle_uploaded_file.

    Args:
        f:
    """
    return f.read().decode('utf-8')

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
            if len(cone_list) > 0:
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
#                wlc.save()
                message += 'Watchlist created successfully with %d sources in %d chunks in %.1f sec' % (len(cone_list), chunks, time.time()-t)
        else:
            wl_id = int(delete)
            watchlist = get_object_or_404(Watchlists, wl_id=wl_id)
            if request.user == watchlist.user:
                watchlist.delete()
                message = 'Watchlist %s deleted successfully' % watchlist.name

# public watchlists belong to the anonymous user
    other_watchlists = Watchlists.objects.filter(public=1)
    if request.user.is_authenticated:
        my_watchlists    = Watchlists.objects.filter(user=request.user)
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
    cursor.execute('SELECT ra, decl, name, radius FROM watchlist_cones WHERE wl_id=%d ' % wl_id)
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
            import os
#            from run_crossmatch import run_watchlist
#            hitlist = run_watchlist(wl_id)
            py = lasair.settings.LASAIR_ROOT + 'anaconda3/envs/lasair/bin/python'
            process = Popen([py, lasair.settings.LASAIR_ROOT + 'lasair-lsst-web/src/utility/run_crossmatch.py', '%d'%wl_id], stdout=PIPE, stderr=PIPE)
            stdout, stderr = process.communicate()

            stdout = stdout.decode('utf-8')
            stderr = stderr.decode('utf-8')
            message += 'watchlist crossmatched [%s, %s]' % (stdout, stderr)

    cursor = connection.cursor()
    cursor.execute('SELECT count(*) AS count FROM watchlist_cones WHERE wl_id=%d' % wl_id)
    for row in cursor:
        number_cones = row[0]

    query = """
SELECT 
c.ra, c.decl, c.name, c.radius, o.objectId, o.ncand, h.arcsec,
o.gmag-o.maggmean AS gdiff, o.rmag-o.magrmean AS rdiff, s.classification
FROM watchlist_cones AS c 
LEFT JOIN watchlist_hits           AS h ON c.cone_id = h.cone_id 
LEFT JOIN objects                  AS o on h.objectId = o.objectId 
LEFT JOIN sherlock_classifications AS s on o.objectId = s.objectId
WHERE c.wl_id=%d ORDER BY o.ncand DESC LIMIT 1000
"""
    cursor.execute(query % wl_id)
    cones = cursor.fetchall()
    conelist = []
    found = 0

    for c in cones:
        d = {'ra'  :c[0], 'decl' :c[1], 'name':c[2]}
        if c[3]: d['radius'] = c[3]
        else:    d['radius'] = watchlist.radius
        if c[4]:   # objectId, means a hit
            found += 1
            d['objectId'] = c[4]
            d['ncand']    = c[5]
            d['arcsec']   = c[6]
            d['gdiff']    = c[7]
            d['rdiff']    = c[8]
            d['sherlock_classification'] = c[9]
        conelist.append(d)

    def first(d):
        """first.

        Args:
            d:
        """
        if 'objectId' in d: 
            if 'ncand' in d:
                return '%04d%s' % (d['ncand'], d['objectId'])
            else:
                return '0000%s' % d['objectId']
        else:
            return '000000000'

    conelist.sort(reverse=True, key=first)

    count = len(conelist)
    
    return render(request, 'show_watchlist.html',{
        'watchlist':watchlist, 
        'conelist' :conelist, 
        'count'    :count, 
        'number_cones': number_cones,
        'is_owner' :is_owner,
        'message'  :message})

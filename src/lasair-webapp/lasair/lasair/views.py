from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponseRedirect, HttpResponse
from django.template.context_processors import csrf
from django.views.decorators.csrf import csrf_exempt
from django.db import connection
from django.db.models import Q
from lasair.models import Myqueries, Annotators
import lasair.settings
import mysql.connector
import json
import math
import time
import utility.date_nid as date_nid
from lasair.objects import obj

from django.contrib.auth.models import User
from django.contrib.auth import login, authenticate

import string
import random
def id_generator(size=10):
    """id_generator.

    Args:
        size:
    """
    chars = string.ascii_lowercase + string.ascii_uppercase + string.digits
    return ''.join(random.choice(chars) for _ in range(size))

def signup(request):
    """signup.

    Args:
        request:
    """
    if request.method == 'POST':
        first_name    = request.POST['first_name']
        last_name     = request.POST['last_name']
        username      = request.POST['username']
        email         = request.POST['email']
        password      = id_generator(10)
        user = User.objects.create_user(username=username, first_name=first_name,last_name=last_name, email=email, password=password)
        user.save()
        return redirect('/accounts/password_reset/')
    else:
        return render(request, 'signup.html')

def connect_db():
    """connect_db.
    """
    msl = mysql.connector.connect(
        user    =lasair.settings.READONLY_USER,
        password=lasair.settings.READONLY_PASS,
        host    =lasair.settings.DATABASES['default']['HOST'],
        port    =lasair.settings.DATABASES['default']['PORT'],
        database='ztf')
    return msl

def status_today(request):
    nid  = date_nid.nid_now()
    return status(request, nid)

def status(request, nid):
    message = ''
    web_domain = lasair.settings.WEB_DOMAIN
    try:
        filename = '%s_%d.json' % (lasair.settings.SYSTEM_STATUS, nid)
        jsonstr = open(filename).read()
    except:
        jsonstr = ''
        return render(request, 'error.html', {'message': 'Cannot open status file for nid=%d'%nid})

    try:
        status = json.loads(jsonstr)
    except:
        status = None
        return render(request, 'error.html', {'message': 'Cannot parse status file for nid=%d'%nid})

    if status and 'today_filter' in status:
        status['today_singleton'] = \
            status['today_filter'] - status['today_filter_out'] - status['today_filter_ss']

    date = date_nid.nid_to_date(nid)
    return render(request, 'status.html', 
            {'web_domain': web_domain, 'status':status, 'date':date, 'message':message})

def index(request):
    """index.
    Args:
        request:
    """
    web_domain = lasair.settings.WEB_DOMAIN
    return render(request, 'index.html', {'web_domain': web_domain})

def index2(request):
    """index.

    Args:
        request:
    """
    web_domain = lasair.settings.WEB_DOMAIN

    objectIds = ['ZTF17aaatdwi', 'ZTF17aabjwwr', 'ZTF18aaawcta']
    datas = []
    json_datas = []
    jdnow = time.time()/86400 + 2440587.5
    message = ''
    for objectId in objectIds:
        d = obj(objectId)
        fewcand = []
        for c in d['candidates']:
            if 'candid' in c:
                if len(fewcand) > 9 or jdnow - c['jd'] > 30:
                    break
                fewcand.append(c)
                mjdmin_ago = jdnow - c['jd']
        d['candidates'] = fewcand
        d['json'] = json.dumps(d)
        d['objectData']['mjdmin_ago'] = mjdmin_ago
        if len(fewcand) > 1:
            datas.append(d)


    return render(request, 'index2.html', {
        'datas':datas, 'message':message,
        })

def about(request):
    """about.

    Args:
        request:
    """
    return render(request, 'about.html')

def cookbook(request, topic):
    """cookbook.

    Args:
        request:
        topic:
    """
    return render(request, 'cookbook/%s.html'%topic, {'topic':topic})

def distance(ra1, de1, ra2, de2):
    """distance.

    Args:
        ra1:
        de1:
        ra2:
        de2:
    """
    dra = (ra1 - ra2)*math.cos(de1*math.pi/180)
    dde = (de1 - de2)
    return math.sqrt(dra*dra + dde*dde)

def sexra(tok):
    """sexra.

    Args:
        tok:
    """
    return 15*(float(tok[0]) + (float(tok[1]) + float(tok[2])/60)/60)

def sexde(tok):
    """sexde.

    Args:
        tok:
    """
    if tok[0].startswith('-'):
        de = (float(tok[0]) - (float(tok[1]) + float(tok[2])/60)/60)
    else:
        de = (float(tok[0]) + (float(tok[1]) + float(tok[2])/60)/60)
    return de

def readcone(cone):
    """readcone.

    Args:
        cone:
    """
    error = False
    message = ''
    cone = cone.replace(',', ' ').replace('\t',' ').replace(';',' ').replace('|',' ')
    tok = cone.strip().split()
#    message += str(tok)

# if tokens begin with 'SN' or 'AT', must be TNS identifier
    TNSname = None
    if len(tok) == 1:
        t = tok[0]
        if t[0:2] == 'SN' or t[0:2] == 'AT':
            return {'TNSprefix':t[0:2], 'TNSname': t[2:]}
        if t[0:2] == '20':
            return {'TNSprefix': '',      'TNSname': t}
        if t[0:3] == 'ZTF':
            return {'objectIds': tok}

# if odd number of tokens, must end with radius in arcsec
    radius = 5.0
    if len(tok)%2 == 1:
        try:
           radius = float(tok[-1])
        except:
            error = True
        tok = tok[:-1]

# remaining options tok=2 and tok=6
#   radegrees decdegrees
#   h:m:s   d:m:s
#   h m s   d m s
    if len(tok) == 2:
        try:
            ra = float(tok[0])
            de = float(tok[1])
        except:
            try:
                ra = sexra(tok[0].split(':'))
                de = sexde(tok[1].split(':'))
            except:
                error = True

    if len(tok) == 6:
        try:
            ra = sexra(tok[0:3])
            de = sexde(tok[3:6])
        except:
            error = True

    if error:
        return {'message': 'cannot parse ' + cone + ' ' + message}
    else:
        message += 'RA,Dec,radius=%.5f,%.5f,%.1f' % (ra, de, radius)
        return {'ra':ra, 'dec':de, 'radius':radius, 'message':message}

def fitsview(request, filename):
    """fitsview.

    Args:
        request:
    """
    return render(request, 'fitsview.html', {'filename':filename})

def conesearch(request):
    """conesearch.

    Args:
        request:
    """
    if request.method == 'POST':
        cone = request.POST['cone']
        json_checked = False
        if 'json' in request.POST and request.POST['json'] == 'on':
            json_checked = True

        data = conesearch_impl(cone)
        if json_checked:
            return HttpResponse(json.dumps(data, indent=2), content_type="application/json")
        else:
            return render(request, 'conesearch.html', {'data':data})
    else:
        return render(request, 'conesearch.html', {})

def conesearch_impl(cone):
    """conesearch_impl.

    Args:
        cone:
    """
    ra = dec = radius = 0.0
#    hitdict = {}
    hitlist = []
    d = readcone(cone)

    if 'objectIds' in d:
        data = {'cone':cone, 'hitlist': d['objectIds'], 
            'message': 'Found ZTF object names'}
        return data

    if 'TNSname' in d:
        cursor = connection.cursor()
        query = 'SELECT objectId FROM watchlist_hits WHERE wl_id=%d AND name="%s"' 
        query = query % (lasair.settings.TNS_WATCHLIST_ID, d['TNSname'])
        cursor.execute(query)
        hits = cursor.fetchall()
        message = '%s not found in TNS'%cone
        for hit in hits:
            hitlist.append(hit[0])
            message = '%s found in TNS'%cone
        data = {'TNSname':d['TNSname'], 'hitlist': hitlist, 'message': message}
        return data
            
    if 'ra' in d:
        ra = d['ra']
        dec = d['dec']
        radius = d['radius']
        dra = radius/(3600*math.cos(dec*math.pi/180))
        dde = radius/3600
        cursor = connection.cursor()
        query = 'SELECT objectId,ramean,decmean FROM objects WHERE ramean BETWEEN %f and %f AND decmean BETWEEN %f and %f' % (ra-dra, ra+dra, dec-dde, dec+dde)
#        query = 'SELECT DISTINCT objectId FROM candidates WHERE ra BETWEEN %f and %f AND decl BETWEEN %f and %f' % (ra-dra, ra+dra, dec-dde, dec+dde)
        cursor.execute(query)
        hits = cursor.fetchall()
        for hit in hits:
#            dist = distance(ra, dec, hit[1], hit[2]) * 3600.0
#            if dist < radius:
#                hitdict[hit[0]] = (hit[1], hit[2], dist)
             hitlist.append(hit[0])
        message = d['message'] + '<br/>%d objects found in cone' % len(hitlist)
        data = {'ra':ra, 'dec':dec, 'radius':radius, 'cone':cone,
                'hitlist': hitlist, 'message': message}
        return data
    else:
        data = {'cone':cone, 'message': d['message']}
        return data

def coverage(request):
    """coverage.

    Args:
        request:
    """
    # if this is a POST request we need to process the form data
    if request.method == 'POST':
        date1 = request.POST['date1'].strip()
        date2 = request.POST['date2'].strip()
        if date1 == 'today': date1 = date_nid.nid_to_date(date_nid.nid_now())
        if date2 == 'today': date2 = date_nid.nid_to_date(date_nid.nid_now())
    else:
#        date1 = '20180528'
        date2 = date_nid.nid_to_date(date_nid.nid_now())
        date1 = '20180528'

    nid1 = date_nid.date_to_nid(date1)
    nid2 = date_nid.date_to_nid(date2)
    return render(request, 'coverage.html',{'nid1':nid1, 'nid2': nid2, 'date1':date1, 'date2':date2})

def streams(request, topic):
    """stream.

    Args:
        request:
        topic:
    """
    try:
        data = open(lasair.settings.BLOB_STORE_ROOT + '/streams/%s' % topic, 'r').read()
    except:
        return render(request, 'error.html', {'message': 'Cannot find log file for ' + topic})
    table = json.loads(data)['digest']
    n = len(table)
    return render(request, 'streams.html', {'topic':topic, 'n':n, 'table':table})

def annotators(request):
    anns = Annotators.objects.filter().order_by('topic')
    annotators = []
    for a in anns:
        d = {
            'usersname'  :a.user.first_name +' '+ a.user.last_name,
            'topic'       :a.topic,
            'description':a.description
        }
        annotators.append(d)

    return render(request, 'annotators.html', {'annotators': annotators})

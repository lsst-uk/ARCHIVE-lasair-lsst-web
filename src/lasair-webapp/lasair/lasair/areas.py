from django.shortcuts import render, get_object_or_404
from django.template.context_processors import csrf
from django.views.decorators.csrf import csrf_exempt
from django.db import connection
from django.contrib.auth.models import User
from django.http import HttpResponse, FileResponse
import lasair.settings
from lasair.models import Areas, AreaHits
import mysql.connector
import json
from random import randrange
from subprocess import Popen, PIPE
import time
import base64
from mocpy import MOC, World2ScreenMPL
from astropy.coordinates import Angle, SkyCoord
import astropy.units as u
import matplotlib.pyplot as plt
import io

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

def bytes2string(bytes):
    """bytes2string.

    Args:
        bytes:
    """
    base64_bytes   = base64.b64encode(bytes)
    str = base64_bytes.decode('utf-8')
    return str

def string2bytes(str):
    """string2bytes.

    Args:
        str:
    """
    base64_bytes  = str.encode('utf-8')
    bytes = base64.decodebytes(base64_bytes)
    return bytes

def make_image_of_MOC(fits_bytes):
    """make_image_of_MOC.

    Args:
        fits_bytes:
    """
    inbuf = io.BytesIO(fits_bytes)
    try:
        moc = MOC.from_fits(inbuf)
    except:
        return render(request, 'error.html', {'message': 'Cannot make MOC from given file'})

    notmoc = moc.complement()

    fig = plt.figure(111, figsize=(10, 5))
    with World2ScreenMPL(fig, fov=360 * u.deg, projection="AIT") as wcs:
        ax = fig.add_subplot(1, 1, 1, projection=wcs)
        notmoc.fill(ax=ax, wcs=wcs, alpha=1.0, fill=True, color="lightgray", linewidth=None)
        moc.fill   (ax=ax, wcs=wcs, alpha=1.0, fill=True, color="red", linewidth=None)
        moc.border(ax=ax, wcs=wcs, alpha=1, color="red")

    plt.grid(color="black", linestyle="dotted")
    outbuf = io.BytesIO()
    plt.savefig(outbuf, format='png', bbox_inches='tight', dpi=200)
    bytes = outbuf.getvalue()
    outbuf.close()
    return bytes

def area_new(request):
    return render(request, 'area_new.html',
        {'random': '%d'%randrange(1000),
        'authenticated': request.user.is_authenticated
        })

@csrf_exempt
def areas_home(request):
    """areas_home.

    Args:
        request:
    """
    message = ''
    if request.method == 'POST' and request.user.is_authenticated:
        delete      = request.POST.get('delete')

        if delete == None:   # create new area

            t = time.time()
            name           = request.POST.get('name')
            description    = request.POST.get('description')

            if 'area_file' in request.FILES:
                fits_bytes  = (request.FILES['area_file']).read()
                fits_string = bytes2string(fits_bytes)
                png_bytes   = make_image_of_MOC(fits_bytes)
                png_string  = bytes2string(png_bytes)

                area = Areas(user=request.user, name=name, description=description, 
                    moc=fits_string, mocimage=png_string, active=0)
                area.save()
                message += '\nArea created successfully in %.1f sec' % (time.time()-t)
            else:
                message = '\nNo file in upload'
        else:
            ar_id = int(delete)
            area = get_object_or_404(Areas, ar_id=ar_id)
            if request.user == area.user:
                area.delete()
                message = 'Area %s deleted successfully' % area.name

    other_areas = Areas.objects.filter(public=1)
    if request.user.is_authenticated:
        my_areas    = Areas.objects.filter(user=request.user)
    else:
        my_areas    = []


    return render(request, 'areas_home.html',
        {'my_areas': my_areas, 
        'random': '%d'%randrange(1000),
        'other_areas': other_areas, 
        'authenticated': request.user.is_authenticated,
        'message': message})

def show_area_file(request, ar_id):
    """show_area_file.

    Args:
        request:
        ar_id:
    """
    message = ''
    area = get_object_or_404(Areas, ar_id=ar_id)

    is_owner = (request.user.is_authenticated) and (request.user == area.user)
    is_public = (area.public == 1)
    is_visible = is_owner or is_public
    if not is_visible:
        return render(request, 'error.html',{
            'message': "This area is private and not visible to you"})

    moc = string2bytes(area.moc)

    filename = area.name + '%d.fits'%randrange(1000)
    f = open('/home/ubuntu/tmp/%s' % filename, 'wb')
    f.write(moc)
    f.close()

    r = HttpResponse(moc)
    r['Content-Type'] = "application/fits"
    r['Content-Disposition'] = 'attachment; filename="%s"' % filename
    return r

def show_area(request, ar_id):
    """show_area.

    Args:
        request:
        ar_id:
    """
    message = ''
    area = get_object_or_404(Areas, ar_id=ar_id)

    is_owner = (request.user.is_authenticated) and (request.user == area.user)
    is_public = (area.public == 1)
    is_visible = is_owner or is_public
    if not is_visible:
        return render(request, 'error.html',{
            'message': "This area is private and not visible to you"})

    if request.method == 'POST' and is_owner:
        if 'name' in request.POST:
            area.name        = request.POST.get('name')
            area.description = request.POST.get('description')

            if request.POST.get('active'): area.active  = 1
            else:                          area.active  = 0

            if request.POST.get('public'): area.public  = 1
            else:                          area.public  = 0

            area.save()
            message += 'area updated'

    cursor = connection.cursor()
    cursor.execute('SELECT count(*) AS count FROM area_hits WHERE ar_id=%d' % ar_id)
    for row in cursor:
        count = row[0]

    cursor.execute('SELECT objectId FROM area_hits WHERE ar_id=%d LIMIT 1000' % ar_id)
    objIds = []
    for row in cursor:
        objIds.append(row[0])
    
    return render(request, 'show_area.html',{
        'area':area, 
        'objIds' :objIds, 
        'mocimage':area.mocimage,
        'count'    :count, 
        'is_owner' :is_owner,
        'message'  :message})

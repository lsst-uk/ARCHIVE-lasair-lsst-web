#from django.shortcuts import render_to_response, get_object_or_404
from django.shortcuts import get_object_or_404
from django.http import HttpResponse, HttpResponseRedirect
from django.template.context_processors import csrf
import lasair.settings
import mysql.connector
from django.http import JsonResponse
from utility.objectStore import objectStore
#import zlib
#import fastavro

def fits(request, candid_cutoutType):
    # cutoutType can be cutoutDifference, cutoutTemplate, cutoutScience
    image_store = objectStore(suffix = 'fits', fileroot=lasair.settings.BLOB_STORE_ROOT + '/fits')
    try:
        fitsdata = image_store.getFileObject(candid_cutoutType)
    except:
        fitsdata = ''
    response = HttpResponse(fitsdata, content_type='image/fits')
    response['Content-Disposition'] = 'attachment; filename="%s.fits"' % candid_cutoutType
    return response

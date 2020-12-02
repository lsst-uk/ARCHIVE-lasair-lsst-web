#from django.shortcuts import render_to_response, get_object_or_404
from django.shortcuts import get_object_or_404
from django.http import HttpResponse, HttpResponseRedirect
from django.template.context_processors import csrf
import lasair.settings
import mysql.connector
from django.http import JsonResponse
import zlib
from utility.objectStore import objectStore
import fastavro

def fits(request, objectId_cutoutType):
    # cutoutType can be cutoutDifference, cutoutTemplate, cutoutScience
    tok = objectId_cutoutType.split('_')
    objectId = tok[0]
    cutoutType = tok[1]
    avro = objectStore(suffix = 'avro', fileroot=lasair.settings.BLOB_STORE_ROOT + '/avro')
    avro_fp = avro.getFileObject(objectId)
    for record in fastavro.reader(avro_fp):
         contentgz = record[cutoutType]['stampData']
         content = zlib.decompress(contentgz, 16+zlib.MAX_WBITS)
    response = HttpResponse(content, content_type='image/fits')
    response['Content-Disposition'] = 'attachment; filename="%s_%s.fits"' % (objectId, cutoutType)
    return response

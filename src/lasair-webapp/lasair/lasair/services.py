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

def connect_db():
    """connect_db.
    """
    msl = mysql.connector.connect(
        user    =lasair.settings.READONLY_USER,
        password=lasair.settings.READONLY_PASS,
        host    =lasair.settings.DATABASES['default']['HOST'],
        database='ztf')
    return msl

def coverageAjax(request, nid1, nid2):
    """Show a specific transient"""

    msl = connect_db()
    cursor = msl.cursor(buffered=True, dictionary=True)
    if nid1 <= nid2:   # date range
        dict = {'queryType': 'dateRange', 'nid1':nid1, 'nid2':nid2}
        query = "SELECT field,fid,ra,decl,SUM(n) as sum "
        query += "FROM coverage WHERE nid BETWEEN %d and %d GROUP BY field,fid,ra,decl" % (nid1, nid2)

    else:              # all dates
        dict = {'queryType': 'allDates'}
        query = "SELECT field,fid,ra,decl,SUM(n) as sum "
        query += "FROM coverage GROUP BY field,fid,ra,decl"

    cursor.execute(query)
    result = []
    for row in cursor:
        result.append({\
            'field':row['field'], \
            'fid'  :row['fid'], \
            'ra'   :row['ra'], \
            'dec'  :row['decl'], 
            'n'    :int(row['sum'])})

    dict['result'] = result
    return JsonResponse(dict)

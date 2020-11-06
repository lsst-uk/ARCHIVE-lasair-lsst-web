#from django.shortcuts import render_to_response, get_object_or_404
from django.shortcuts import get_object_or_404
from django.http import HttpResponse, HttpResponseRedirect
from django.template.context_processors import csrf
import lasair.settings
import mysql.connector
from django.http import JsonResponse
import gzip
from utility.objectStore import objectStore

def fits(request, filename):
# examples of image file name
# candid1189406621015015005_pid1189406621015_targ_sci
# candid1189406621015015005_ref
# candid1189406621015015005_pid1189406621015_targ_scimref
    fitsos = objectStore(suffix = 'fits.gz',
        fileroot=lasair.settings.BLOB_STORE_ROOT + '/fits')
    cephfilename = fitsos.getFileName(filename)
    with gzip.open(cephfilename, 'rb') as f:
        content = f.read()
    response = HttpResponse(content, content_type='image/fits')
    response['Content-Disposition'] = 'attachment; filename="%s.fits"' % filename
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

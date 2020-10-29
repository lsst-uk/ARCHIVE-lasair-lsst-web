from rest_framework import serializers
from gkutils.commonutils import coneSearchHTM, FULL, QUICK, CAT_ID_RA_DEC_COLS, base26, Struct
from datetime import datetime
from django.db import connection
from django.db import IntegrityError
import lasair.settings
import requests
import json

CAT_ID_RA_DEC_COLS['objects'] = [['objectId', 'ramean', 'decmean'],1018]

REQUEST_TYPE_CHOICES = (
        ('count', 'Count'),
        ('all', 'All'),
        ('nearest', 'Nearest'),
    )

class ConeSerializer(serializers.Serializer):
    ra          = serializers.FloatField(required=True)
    dec         = serializers.FloatField(required=True)
    radius      = serializers.FloatField(required=True)
    requestType = serializers.ChoiceField(choices=REQUEST_TYPE_CHOICES)

    def save(self):

        ra          = self.validated_data['ra']
        dec         = self.validated_data['dec']
        radius      = self.validated_data['radius']
        requestType = self.validated_data['requestType']


        # Get the authenticated user, if it exists.
        userId = 'unknown'
        request = self.context.get("request")
        if request and hasattr(request, "user"):
            userId = request.user

        print (userId)

        if radius > 1000:
            replyMessage = "Max radius is 1000 arcsec."
            info = { "error": replyMessage }
            return info

        replyMessage = 'No object found'
        info = {"info": replyMessage}

        # Is there an object within RADIUS arcsec of this object? - KWS - need to fix the gkhtm code!!
        message, results = coneSearchHTM(ra, dec, radius, 'objects', queryType = QUICK, conn = connection, django = True, prefix='htm', suffix = '')

        obj = None
        separation = None

        objectList = []
        if len(results) > 0:
            if requestType == "nearest":
                obj = results[0][1]['objectId']
                separation = results[0][0]
                replyMessage = 'Success'
                info = { "object": obj, "info": replyMessage, "separation": separation }
            elif requestType == "all":
                replyMessage = 'Success'
                for row in results:
                    objectList.append({"object": row[1]["objectId"], "separation": row[0]})
                info = { "objects": objectList, "info": replyMessage }
            elif requestType == "count":
                replyMessage = 'Success'
                info = { "objectCount": len(results), "info": replyMessage }
            else:
                info = { "error": "Invalid request type" }

        return info

class StreamlogSerializer(serializers.Serializer):
    topic = serializers.SlugField(required=True)
    max   = serializers.IntegerField(required=False, default=1000)

    def save(self):
        topic = self.validated_data['topic']
        max = self.validated_data['max']

        # Get the authenticated user, if it exists.
        userId = 'unknown'
        request = self.context.get("request")
        if request and hasattr(request, "user"):
            userId = request.user

        try:
            data = open(lasair.settings.BLOB_STORE_ROOT + '/logs/%s' % topic, 'r').read()
            data = json.loads(data)
            datalist = data['digest'][:max]
            data['digest'] = datalist
            replyMessage = 'Success'
        except:
            data = {'digest':[]}
            replyMessage = 'No alerts'
        info = { "jsonStreamLog": data, "info": replyMessage }
        return info

class SherlockObjectSerializer(serializers.Serializer):
    objectId = serializers.SlugField(required=True)
    lite     = serializers.BooleanField()

    def save(self):
        objectId = self.validated_data['objectId']
        lite     = self.validated_data['lite']

        # Get the authenticated user, if it exists.
        userId = 'unknown'
        request = self.context.get("request")
        if request and hasattr(request, "user"):
            userId = request.user

        url = 'http://%s/object/%s' % (lasair.settings.SHERLOCK_SERVICE, objectId)
        if lite:
            url += '?lite=true'
        r = requests.get(url)
        try:
            data = json.loads(r.text)
            replyMessage = 'Success'
        except:
            data = ''
            replyMessage = r.text
        info = { "data": data, "info": replyMessage }
        return info

class SherlockQuerySerializer(serializers.Serializer):
    ra          = serializers.FloatField(required=True)
    dec         = serializers.FloatField(required=True)
    lite        = serializers.BooleanField()

    def save(self):
        ra          = self.validated_data['ra']
        dec         = self.validated_data['dec']
        lite        = self.validated_data['lite']

        # Get the authenticated user, if it exists.
        userId = 'unknown'
        request = self.context.get("request")
        if request and hasattr(request, "user"):
            userId = request.user

        url = 'http://%s/query?ra=%f&dec=%f' % (lasair.settings.SHERLOCK_SERVICE, ra, dec)
        if lite:
            url += '&lite=true'
        r = requests.get(url)
        try:
            data = json.loads(r.text)
            replyMessage = 'Success'
        except:
            data = ''
            replyMessage = r.text

        info = { "data": data, "info": replyMessage }
        return info

from utility import query_utilities
import mysql.connector

def connect_db():
    msl = mysql.connector.connect(
        user    =lasair.settings.READONLY_USER,
        password=lasair.settings.READONLY_PASS,
        host    =lasair.settings.DATABASES['default']['HOST'],
        database='ztf')
    return msl

class QuerySerializer(serializers.Serializer):
    selected   = serializers.CharField(max_length=1024, required=True)
    tables     = serializers.CharField(max_length=1024, required=True)
    conditions = serializers.CharField(max_length=1024, required=True)

    def save(self):
        selected   = self.validated_data['selected']
        tables     = self.validated_data['tables']
        conditions = self.validated_data['conditions']

        # Get the authenticated user, if it exists.
        userId = 'unknown'
        request = self.context.get("request")
        if request and hasattr(request, "user"):
            userId = request.user

        page = 0
        if userId == 'dummy':
            perpage = 1000
            limitseconds = 300
        else:
            perpage = 10000
            limitseconds = 3000

        sqlquery_real = query_utilities.make_query(selected, tables, conditions, page, perpage, limitseconds)
        msl = connect_db()
        cursor = msl.cursor(buffered=True, dictionary=True)

        result = []
        try:
            cursor.execute(sqlquery_real)
            for row in cursor: result.append(row)
            message = 'Success for user %s' % userId
        except Exception as e:
            message = 'Your query:<br/><b>' + sqlquery_real + '</b><br/>returned the error<br/><i>' + str(e) + '</i>'

        query = {'selected':selected, 'tables':tables, 'conditions':conditions}
        info = { "query": query, "result":result, "info": message }
        return info

def get_lightcurve(objectId):
    lightcurves = objectStore(suffix = 'json',
        fileroot=lasair.settings.BLOB_STORE_ROOT + '/lightcurve/')

    alertjson = lightcurves.getObject(objectId)
    alert = json.loads(alertjson)
    candidates = []
    candlist = alert['prv_candidates'] + [alert['candidate']]
    candidates = []
    for cand in candlist:
        row = {}
        for key in ['candid', 'fid', 'magpsf', 'sigmapsf', 'isdiffpos']:
            if key in cand: row[key] = cand[key]
        row['mjd'] = mjd = float(cand['jd']) - 2400000.5
        if cand['candid']:
            candidates.append(row)
    return candidates

def get_lightcurves(objectIds):
    ncand = 0
    lightcurves = {}
    for objectId in objectIds:
        lightcurve = get_lightcurve(objectId)
        ncand += len(lightcurve)
        lightcurves[objectId] = lightcurve
    return {'ncand':ncand, 'data':lightcurves}

from utility.objectStore import objectStore
class LightcurvesSerializer(serializers.Serializer):
    objectIdsTxt = serializers.CharField(max_length=16384, required=True)
    def save(self):
        objectIdsTxt = self.validated_data['objectIdsTxt']
        objectIds = []
        for tok in objectIdsTxt.split(','):
            objectIds.append(tok.strip())

        # Get the authenticated user, if it exists.
        userId = 'unknown'
        request = self.context.get("request")
        if request and hasattr(request, "user"):
            userId = request.user

        lightcurves = get_lightcurves(objectIds)
        replyMessage = 'Success'
        info = { "lightcurves": lightcurves, "info": replyMessage }
        return info

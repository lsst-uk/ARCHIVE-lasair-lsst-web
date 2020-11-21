from rest_framework import serializers
from gkutils.commonutils import coneSearchHTM, FULL, QUICK, CAT_ID_RA_DEC_COLS, base26, Struct
from datetime import datetime
from django.db import connection
from django.db import IntegrityError
import lasair.settings
import requests
import json
import re
import fastavro

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

        replyMessage = 'No object found ra=%.5f dec=%.5f radius=%.2f' % (ra, dec, radius)
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

class SherlockObjectsSerializer(serializers.Serializer):
    objectIds = serializers.CharField(required=True)
    lite      = serializers.BooleanField()

    def save(self):
        objectIds = None
        lite = False
        objectIds = self.validated_data['objectIds']

        if 'lite' in self.validated_data:
            lite      = self.validated_data['lite']

        # Get the authenticated user, if it exists.
        userId = 'unknown'
        request = self.context.get("request")
        if request and hasattr(request, "user"):
            userId = request.user

        datadict = {}
        objects = objectIds.split(',')
        n = 0
        for o in objects:
            url = 'http://%s/object/%s' % (lasair.settings.SHERLOCK_SERVICE, o.strip())
            if lite: url += '?lite=true'
            r = requests.get(url)
            try:
                datadict[o] = json.loads(r.text)
                n += 1
            except:
                datadict[o] = "not found"
        replyMessage = '%d objects resolved' % n
        return { "data": datadict, "info": replyMessage }

class SherlockPositionSerializer(serializers.Serializer):
    ra        = serializers.FloatField(required=True)
    dec       = serializers.FloatField(required=True)
    lite      = serializers.BooleanField()

    def save(self):
        lite = False
        ra        = self.validated_data['ra']
        dec       = self.validated_data['dec']
        if 'lite' in self.validated_data:
            lite      = self.validated_data['lite']

        # Get the authenticated user, if it exists.
        userId = 'unknown'
        request = self.context.get("request")
        if request and hasattr(request, "user"):
            userId = request.user

        url = 'http://%s/query?ra=%f&dec=%f' % (lasair.settings.SHERLOCK_SERVICE, ra, dec)
        if lite: url += '&lite=true'
        r = requests.get(url)
        try:
            data = json.loads(r.text)
            replyMessage = 'Success'
        except:
            data = ''
            replyMessage = 'r.text'
        return { "data": data, "info": replyMessage }

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

class StreamsSerializer(serializers.Serializer):
    topic = serializers.SlugField(required=False)
    limit   = serializers.IntegerField(required=False)
    regex = serializers.CharField(required=False)

    def save(self):
        topic = None
        if 'topic' in self.validated_data:
            topic = self.validated_data['topic']

        limit = None
        if 'limit' in self.validated_data:
            limit = self.validated_data['limit']

        regex = None
        if 'regex' in self.validated_data:
            regex = self.validated_data['regex']

        if not topic and not regex:
            regex = '.*'

        # Get the authenticated user, if it exists.
        userId = 'unknown'
        request = self.context.get("request")
        if request and hasattr(request, "user"):
            userId = request.user

        if topic:
            if 1:
                datafile = open(lasair.settings.BLOB_STORE_ROOT + '/streams/%s' % topic, 'r').read()
                data = json.loads(datafile)['digest']
                if limit: data = data[:limit]
                replyMessage = 'Success'
            else:
                replyMessage = 'No alerts'
            info = { "data": data, "info": replyMessage }
            return info

        if regex:
            try:
                r = re.compile(regex)
            except:
                replyMessage = '%s is not a regular expression' % regex
                return { "topics": [], "info": replyMessage }

            msl = connect_db()
            cursor = msl.cursor(buffered=True, dictionary=True)
            result = []
            query = 'SELECT mq_id, user, name FROM myqueries WHERE active>0'
            cursor.execute(query)
            for row in cursor: 
                tn = query_utilities.topic_name(row['user'], row['name'])
                if r.match(tn):
                    td = {'topic':tn, 'more_info':'https://lasair-iris.roe.ac.uk/query/%d/' % row['mq_id']}
                    result.append(td)
            replyMessage = 'Success for regex %s' % regex
            info = { "topics": result, "info": replyMessage }
            return info

        return { "info": 'Must supply either topic or regex' }

def get_lightcurve(objectId):
    avro = objectStore(suffix = 'avro',
        fileroot=lasair.settings.BLOB_STORE_ROOT + '/avro')

    try:
        avro_fp = avro.getFileObject(objectId)
    except:
        message = 'objectId %s does not exist'%objectId
        data = {'objectId':objectId, 'message':message}
        return data

    alert = {}
    for record in fastavro.reader(avro_fp):
        for k,v in record.items():
            if k not in ['cutoutDifference', 'cutoutTemplate', 'cutoutScience']:
                alert[k] = v
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
    objectIds = serializers.CharField(max_length=16384, required=True)
    def save(self):
        objectIds = self.validated_data['objectIds']
        olist = []
        for tok in objectIds.split(','):
            olist.append(tok.strip())

        # Get the authenticated user, if it exists.
        userId = 'unknown'
        request = self.context.get("request")
        if request and hasattr(request, "user"):
            userId = request.user

        lightcurves = get_lightcurves(olist)
        replyMessage = 'Success'
        info = { "lightcurves": lightcurves, "info": replyMessage }
        return info

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
import datetime

def record_user(userId, service):
    f = open('/home/ubuntu/lasair-lsst-web/src/lasair-webapp/lasair/static/api_users.txt', 'a')
    now_number = datetime.datetime.utcnow()
    utc = now_number.strftime("%Y-%m-%d %H:%M:%S")
    s = '%s, %s, %s\n' % (utc, userId, service)
    f.write(s)
    f.close()

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
            record_user(userId, 'cone')

        if radius > 1000:
            replyMessage = "Max radius is 1000 arcsec."
            info = { "error": replyMessage }
            return info

        replyMessage = 'No object found ra=%.5f dec=%.5f radius=%.2f' % (ra, dec, radius)
        info = {"error": replyMessage}

        # Is there an object within RADIUS arcsec of this object? - KWS - need to fix the gkhtm code!!
        message, results = coneSearchHTM(ra, dec, radius, 'objects', queryType = QUICK, conn = connection, django = True, prefix='htm', suffix = '')

        obj = None
        separation = None

        objectList = []
        if len(results) > 0:
            if requestType == "nearest":
                obj = results[0][1]['objectId']
                separation = results[0][0]
                info = { "object": obj, "separation": separation }
            elif requestType == "all":
                for row in results:
                    objectList.append({"object": row[1]["objectId"], "separation": row[0]})
                info = objectList
            elif requestType == "count":
                info = {'count': len(results)}
            else:
                info = { "error": "Invalid request type" }

        return info

from lasair.objects import objjson
class ObjectsSerializer(serializers.Serializer):
    objectIds = serializers.CharField(required=True)

    def save(self):
        objectIds = self.validated_data['objectIds']

        olist = []
        for tok in objectIds.split(','):
            olist.append(tok.strip())
#        olist = olist[:10] # restrict to 10

        # Get the authenticated user, if it exists.
        userId = 'unknown'
        request = self.context.get("request")
        if request and hasattr(request, "user"):
            userId = request.user
            record_user(userId, 'object')

        result = []  
        for objectId in olist:
            result.append(objjson(objectId))
        return result

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
            record_user(userId, 'sherlockobjects')

        datadict = {}
        url = 'http://%s/object/%s' % (lasair.settings.SHERLOCK_SERVICE, objectIds)
        if lite: url += '?lite=true'
        r = requests.get(url)
        if r.status_code == 200:
            return r.json()
        else: 
            return {"error": r.text}

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
            record_user(userId, 'sherlockposition')
# can also send multiples, but not yet implemented
# http://192.41.108.29/query?ra=115.811388,97.486925&dec=-25.76404,-26.975506

        url = 'http://%s/query?ra=%f&dec=%f' % (lasair.settings.SHERLOCK_SERVICE, ra, dec)
        if lite: url += '&lite=true'
        r = requests.get(url)
        if r.status_code != 200:
            return {"error":  r.text}
        else:
            return json.loads(r.text)

from lasair.query_builder import check_query, build_query
import mysql.connector

def connect_db_readonly():
    msl = mysql.connector.connect(
        user    =lasair.settings.READONLY_USER,
        password=lasair.settings.READONLY_PASS,
        host    =lasair.settings.DATABASES['default']['HOST'],
        port    =lasair.settings.DB_PORT,
        database='ztf')
    return msl

def connect_db_readwrite():
    msl = mysql.connector.connect(
        user    =lasair.settings.READWRITE_USER,
        password=lasair.settings.READWRITE_PASS,
        host    =lasair.settings.DATABASES['default']['HOST'],
        port    =lasair.settings.DB_PORT,
        database='ztf')
    return msl

class QuerySerializer(serializers.Serializer):
    selected   = serializers.CharField(max_length=4096, required=True)
    tables     = serializers.CharField(max_length=1024, required=True)
    conditions = serializers.CharField(max_length=4096, required=True, allow_blank=True)
    limit      = serializers.IntegerField(max_value=1000000, required=False)
    offset     = serializers.IntegerField(required=False)

    def save(self):
        selected   = self.validated_data['selected']
        tables     = self.validated_data['tables']
        conditions = self.validated_data['conditions']
        limit = None
        if 'limit' in self.validated_data:
            limit      = self.validated_data['limit']
        offset = None
        if 'offset' in self.validated_data:
            offset     = self.validated_data['offset']

        # Get the authenticated user, if it exists.
        userId = 'unknown'
        request = self.context.get("request")
        maxlimit = 1000
        if request and hasattr(request, "user"):
            userId = request.user
            if str(userId) != 'dummy':
                maxlimit = 10000
            for g in request.user.groups.all():
                if g.name == 'powerapi':
                    maxlimit = 1000000
            record_user(userId, 'query')

        page = 0
        limitseconds = 300

        if limit == None: limit = 1000
        else:             limit = int(limit)
        limit = min(maxlimit, limit)

        if offset == None: offset = 0
        else:              offset = int(offset)

        error = check_query(selected, tables, conditions)
        if error:
            return {"error":error}

        try:
            sqlquery_real = build_query(selected, tables, conditions)
        except Exception as e:
            return {"error": str(e)}
            
        sqlquery_real += ' LIMIT %d OFFSET %d' % (limit, offset)

        msl = connect_db_readonly()
        cursor = msl.cursor(buffered=True, dictionary=True)
        result = []
        try:
            cursor.execute(sqlquery_real)
            for row in cursor: result.append(row)
            return result
        except Exception as e:
            error = 'Your query:<br/><b>' + sqlquery_real + '</b><br/>returned the error<br/><i>' + str(e) + '</i>'
            return {"error":error}

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
            record_user(userId, 'streams')

        if topic:
            try:
                datafile = open(lasair.settings.BLOB_STORE_ROOT + '/streams/%s' % topic, 'r').read()
                data = json.loads(datafile)['digest']
                if limit: 
                    data = data[:limit]
                return data
            except:
                error = 'Cannot open digest file for topic %s' % topic
                return {"error":error}

        if regex:
            try:
                r = re.compile(regex)
            except:
                replyMessage = '%s is not a regular expression' % regex
                return { "topics": [], "info": replyMessage }

            msl = connect_db_readonly()
            cursor = msl.cursor(buffered=True, dictionary=True)
            result = []
            query = 'SELECT mq_id, user, name, topic_name FROM myqueries WHERE active>0'
            cursor.execute(query)
            for row in cursor: 
                tn = row['topic_name']
                if r.match(tn):
                    td = {'topic':tn, 'more_info':'https://lasair-iris.roe.ac.uk/query/%d/' % row['mq_id']}
                    result.append(td)
            info = result
            return info

        return { "error": 'Must supply either topic or regex' }

from cassandra.cluster import Cluster
from cassandra.query import dict_factory
from utility.objectStore import objectStore
from lasair.lightcurves import lightcurve_fetcher

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
            record_user(userId, 'lightcurves')

            # Fetch the lightcurve, either from cassandra or file system
        if lasair.settings.CASSANDRA_HEAD is not None:
            LF = lightcurve_fetcher(cassandra_hosts=lasair.settings.CASSANDRA_HEAD)
        else:
            LF = lightcurve_fetcher(fileroot=lasair.settings.BLOB_STORE_ROOT+'/objectjson')

        lightcurves = []
        for objectId in olist:
            candidates = LF.fetch(objectId)
            lightcurves.append(candidates)

        LF.close()
        return lightcurves


class AnnotateSerializer(serializers.Serializer):
    topic          = serializers.CharField(max_length=256, required=True)
    objectId       = serializers.CharField(max_length=256, required=True)
    classification = serializers.CharField(max_length=256, required=True)
    version        = serializers.CharField(max_length=256, required=True)
    explanation    = serializers.CharField(max_length=256, required=True, allow_blank=True)
    classdict      = serializers.CharField(max_length=256, required=True)
    url            = serializers.CharField(max_length=256, required=True, allow_blank=True)

    def save(self):
        topic          = self.validated_data['topic']
        objectId       = self.validated_data['objectId']
        classification = self.validated_data['classification']
        version        = self.validated_data['version']
        explanation    = self.validated_data['explanation']
        classdict      = self.validated_data['classdict']
        url            = self.validated_data['url']
        # Get the authenticated user, if it exists.
        userId = 'unknown'
        request = self.context.get("request")
        if request and hasattr(request, "user"):
            userId = request.user
            user_name = userId.first_name +' '+ userId.last_name
            record_user(userId, 'annotate')

        # make sure the user submitting the annotation is the owner of the annotator
        is_owner = False
        try:
            msl = connect_db_readwrite()
            cursor = msl.cursor(buffered=True, dictionary=True)
        except MySQLdb.Error as e:
            return {'error':"Cannot connect to master database %d: %s\n" % (e.args[0], e.args[1])}

        cursor = msl.cursor (dictionary=True)
        cursor.execute ('SELECT * from annotators where topic="%s"' % topic)
        nrow = 0
        for row in cursor:
            nrow += 1
            if row['user'] == userId.id:
                is_owner = True
        if nrow == 0:
            return {'error':"Annotator error: topic %s does not exist" % topic}
        if not is_owner:
            return {'error':"Annotator error: %s is not allowed to submit to topic %s" % (user_name, topic)}

        # form the insert query
        query = 'REPLACE INTO annotations ('
        query += 'objectId, topic, version, classification, explanation, classdict, url'
        query += ') VALUES (' 
        query += "'%s', '%s', '%s', '%s', '%s', '%s', '%s')" 
        query = query % (objectId, topic, version, classification, explanation, classdict, url)

        try:
            cursor = msl.cursor (dictionary=True)
            cursor.execute (query)
            cursor.close ()
            msl.commit()
        except mysql.connector.Error as e:
            return {'error':"Query failed %d: %s\n" % (e.args[0], e.args[1])}

        result = {'status': 'success', 'query':query}
        return result

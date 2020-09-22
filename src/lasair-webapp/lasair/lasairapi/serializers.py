from rest_framework import serializers
from gkutils.commonutils import coneSearchHTM, FULL, QUICK, CAT_ID_RA_DEC_COLS, base26, Struct
from datetime import datetime
from django.db import connection
from django.db import IntegrityError
import lasair.settings
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
        perpage = 1000
        limitseconds = 300
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

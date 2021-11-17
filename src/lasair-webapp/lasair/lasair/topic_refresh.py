import os
import json
import lasair.settings
from datetime import datetime
import mysql.connector
from confluent_kafka import Producer, KafkaError, admin

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

def datetime_converter(o):
# used by json encoder when it gets a type it doesn't understand
    if isinstance(o, datetime.datetime):
        return o.__str__()

def topic_refresh(real_sql, topic, limit=10):
    message = ''
    msl = connect_db()
    cursor = msl.cursor(buffered=True, dictionary=True)
    query = real_sql + ' LIMIT %d' % limit

    try:
        cursor.execute(query)
    except Exception as e:
        message += 'Your query:<br/><b>' + query + '</b><br/>returned the error<br/><i>' + str(e) + '</i><br/>'
        return message

    recent = []
    for record in cursor:
        recorddict = dict(record)
        now_number = datetime.utcnow()
        recorddict['UTC'] = now_number.strftime("%Y-%m-%d %H:%M:%S")
        print(recorddict)
        recent.append(recorddict)

    conf = {
        'bootstrap.servers': lasair.settings.KAFKA_PRODUCER,
        'security.protocol': 'SASL_PLAINTEXT',
        'sasl.mechanisms'  : 'SCRAM-SHA-256',
        'sasl.username'    : 'admin',
        'sasl.password'    : lasair.settings.KAFKA_PASSWORD
    }

    # delete the old topic
    a = admin.AdminClient(conf)

    try:
        result = a.delete_topics([topic])
        result[topic].result()
        time.sleep(1)
    except Exception as e:
        message += 'Topic is ' + topic + '<br/>'
        message += str(e) + '<br/>'

    # pushing in new messages will remake the topic
    try:
        p = Producer(conf)
        for out in recent: 
            jsonout = json.dumps(out, default=datetime_converter)
            p.produce(topic, value=jsonout)
        p.flush(10.0)   # 10 second timeout
        message += 'New messages produced to Kafka<br/>'
    except Exception as e:
        message += "ERROR in queries/topic_refresh: cannot produce to public kafka<br/>" + str(e) + '<br/>'
    return message

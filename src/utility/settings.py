DB_HOST = 'lasair-db'
DB_DATABASE = 'ztf'

DB_USER = 'readonly_ztf'
DB_PASS = 'OPV537car'

DB_USER_WRITE = 'ztf'
DB_PASS_WRITE = 'OPV537'

SHERLOCK_ACCOUNT = 'lasair@lasair-dev-node0'

LASAIR_ROOT = '/home/ubuntu/'

#KAFKA_PRODUCER  = 'public.alerts.ztf.uw.edu'
KAFKA_PRODUCER  = '192.41.108.22'
GROUPID = 'LASAIR-IRIS1'
KAFKA_TIMEOUT = 120.0
KAFKA_THREADS = 8
KAFKA_MAXALERTS = 10000
# ingestion is limited to KAFKA_THREADS * KAFKA_MAXALERTS
INGEST_WAIT_TIME = 60

GRAFANA_USERNAME = 'ztf'
GRAFANA_PASSWORD = 'fullofstars'

LASAIR_USERID    = 54

LASAIR_KAFKA_PRODUCER = 'lasair-dev.roe.ac.uk:9092'



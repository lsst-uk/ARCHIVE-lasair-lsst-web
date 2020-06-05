from django.db import models

class Objects(models.Model):
    primaryid = models.AutoField(db_column='primaryId', primary_key=True)  # Field name made lowercase.
    objectid = models.CharField(db_column='objectId', unique=True, max_length=16, blank=True, null=True)  # Field name made lowercase.
    ncand = models.IntegerField()
    ramean = models.FloatField()
    rastd = models.FloatField()
    decmean = models.FloatField()
    decstd = models.FloatField()
    maggmin = models.FloatField()
    maggmax = models.FloatField()
    maggmedian = models.FloatField()
    maggmean = models.FloatField()
    magrmin = models.FloatField()
    magrmax = models.FloatField()
    magrmedian = models.FloatField()
    magrmean = models.FloatField()
    latestmag = models.FloatField()
    jdmin = models.FloatField()
    jdmax = models.FloatField()

    class Meta:
        managed = False
        db_table = 'objects'

# A watchlist is owned by a user and given a name and description
# Only active watchlists are run against the realtime ingestion
# The prequel_where can be used to select which candidates are compared with the watchlist
from django.contrib.auth.models import User

# When a watchlist is run against the database, ZTF candidates may be matched to cones
# We also keep the objectId of that candidate and distance from the cone center
# If the same run happens again, that candidate will not go in again to the same watchlist.

class WatchlistCones(models.Model):
    cone_id = models.AutoField(primary_key=True)
    wl      = models.ForeignKey('Watchlists', models.DO_NOTHING, blank=True, null=True)
    name    = models.CharField(max_length=32, blank=True, null=True)
    ra      = models.FloatField(blank=True, null=True)
    decl    = models.FloatField(blank=True, null=True)
    radius  = models.FloatField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'watchlist_cones'

class WatchlistHits(models.Model):
    candid   = models.BigIntegerField(primary_key=True)
    wl       = models.ForeignKey('Watchlists', models.DO_NOTHING)
    cone     = models.ForeignKey(WatchlistCones, models.DO_NOTHING, blank=True, null=True)
    objectid = models.CharField(db_column='objectId', max_length=16, blank=True, null=True)  # Field name made lowercase.
    arcsec   = models.FloatField(blank=True, null=True)
    name     = models.CharField(max_length=32, blank=True, null=True)

    class Meta:
        managed         = False
        db_table        = 'watchlist_hits'
        unique_together = (('candid', 'wl'),)

class Watchlists(models.Model):
    wl_id         = models.AutoField(primary_key=True)
    user          = models.ForeignKey(User, models.DO_NOTHING, db_column='user', blank=True, null=True)
    name          = models.CharField(max_length=256, blank=True, null=True)
    description   = models.CharField(max_length=4096, blank=True, null=True)
    active        = models.IntegerField(blank=True, null=True)
    public        = models.IntegerField(blank=True, null=True)
    radius        = models.FloatField(blank=True, null=True)
    timestamp     = models.DateTimeField(auto_now=True, editable=False, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'watchlists'

class Myqueries(models.Model):
    mq_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, models.DO_NOTHING, db_column='user', blank=True, null=True)
    name = models.CharField(max_length=256, blank=True, null=True)
    description = models.CharField(max_length=4096, blank=True, null=True)
    selected = models.CharField(max_length=4096, blank=True, null=True)
    conditions = models.CharField(max_length=4096, blank=True, null=True)
    tables = models.CharField(max_length=4096, blank=True, null=True)
    public = models.IntegerField(blank=True, null=True)
    active = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'myqueries'


class Comments(models.Model):
    comment_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, models.DO_NOTHING, db_column='user', blank=True, null=True)
    objectid = models.CharField(db_column='objectId', unique=True, max_length=16, blank=True, null=True)  # Field name made lowercase.
    content = models.CharField(max_length=4096, blank=True, null=True)
    time = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'comments'


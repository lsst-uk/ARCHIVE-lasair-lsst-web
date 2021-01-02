from rest_framework.throttling import UserRateThrottle
import lasair.settings
import datetime

def logit(s):
    f = open('/home/ubuntu/lasair-lsst-web/src/lasair-webapp/lasair/static/api_users.txt', 'a')
    now_number = datetime.datetime.utcnow()
    utc = now_number.strftime("%Y-%m-%d %H:%M:%S")
    s = '%s: %s\n' % (utc, s)
    f.write(s)
    f.close()

class UserClassRateThrottle(UserRateThrottle):
    scope = 'user'

    def __init__(self):
        super().__init__()

    def allow_request(self, request, view):
        self.key = self.get_cache_key(request, view)
#        logit('%s %s' % (self.scope, self.key))

        if self.key is None:
            return True

        self.history = self.cache.get(self.key, [])
#        logit('%s ' % (self.history))
        self.now = self.timer()

        # Drop any requests from the history which have now passed the
        # throttle duration
        while self.history and self.history[-1] <= self.now - self.duration:
            self.history.pop()
        logit('%d of %d api calls for ...' % (len(self.history), self.num_requests))
        if len(self.history) >= self.num_requests:
            return self.throttle_failure()
        return self.throttle_success()

    def get_cache_key(self, request, view):
        if request.user.is_authenticated:
            ident = request.user.pk
        else:
            ident = self.get_ident(request)

        self.rate = self.get_rate(request)
#        logit( "Throttling rate for %s: %s" % (request.user, self.rate))

        self.num_requests, self.duration = self.parse_rate(self.rate)
        return self.cache_format % {
            'scope': self.scope,
            'ident': ident
        }

    def get_rate(self, request=None):
        """
        Determine the string representation of the allowed request rate.
        """
        if not getattr(self, 'scope', None):
            msg = ("You must set either `.scope` or `.rate` for '%s' throttle" %
                   self.__class__.__name__)
            raise ImproperlyConfigured(msg)

        if request:
            if str(request.user) == 'dummy':
                user_type = "ANON_THROTTLE_RATES"
            else:
                user_type = "USER_THROTTLE_RATES"

            for g in request.user.groups.all():
                if g.name == 'powerapi':
                    user_type = "POWER_THROTTLE_RATES"
#            logit('%s %s' % (str(request.user), user_type))
        else:
            user_type = "DEFAULT_THROTTLE_RATES"

        throttle_rates = lasair.settings.REST_FRAMEWORK[user_type]

        try:
            return throttle_rates[self.scope]
        except KeyError:
            msg = "No default throttle rate set for '%s' scope" % self.scope
            raise ImproperlyConfigured(msg)

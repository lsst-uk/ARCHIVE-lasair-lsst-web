import json
import sys
from cassandra.cluster import Cluster
from cassandra.query import dict_factory

class lightcurve_fetcher_error(Exception):
    def __init__(self, message):
        self.message = message

class lightcurve_fetcher():
    def __init__(self, cassandra_hosts=None, fileroot=None):
        if cassandra_hosts is not None:
            self.using_cassandra = True
            self.cluster = Cluster(cassandra_hosts)
            self.session = self.cluster.connect()
            # Set the row_factory to dict_factory, otherwise
            # the data returned will be in the form of object properties.
            self.session.row_factory = dict_factory
            self.session.set_keyspace('lasair')
        elif fileroot is not None:
            self.using_cassandra = False
            self.fileroot = fileroot
            self.session = None
        else:
            raise lightcurve_fetcher_error('Must give either cassandra_hosts or fileroot')

    def fetch(self, objectId):
        if self.using_cassandra:
            query = "SELECT candid, jd, ra, dec, fid, nid, magpsf, sigmapsf, "
            query += "magnr,sigmagnr, magzpsci, "
            query += "isdiffpos, ssdistnr, ssnamenr, drb "
            query += "from candidates where objectId = '%s'" % objectId
            ret = self.session.execute(query)
            candidates = []
            for cand in ret:
                if cand['isdiffpos'] == '1': 
                    cand['isdiffpos'] = 't'
                if cand['isdiffpos'] == '0': 
                    cand['isdiffpos'] = 'f'
                candidates.append(cand)

            query = "SELECT jd, fid, diffmaglim "
            query += "from noncandidates where objectId = '%s'" % objectId
            ret = self.session.execute(query)
            for cand in ret:
                candidates.append(cand)
            return candidates
        else:
            store = objectStore(suffix = 'json', fileroot=self.fileroot)
            lc = store.getObject(objectId)

            if not lc:
                raise lightcurve_fetcher_error('Object %s does not exist'%objectId)

            try:
                candlist = json.loads(lc)
                candidates = candlist['candidates']
                return candidates
            except:
                print(lc)
                raise lightcurve_fetcher_error('Cannot parse json for object %s' % objectId)

    def close(self):
        if self.session:
            self.cluster.shutdown()

if __name__ == "__main__":
    LF = lightcurve_fetcher(cassandra_hosts = ['192.168.0.11'])

    candidates = LF.fetch('ZTF21abcmlzt')
    print(candidates)

# -*- coding: utf-8 -*-
"""

    Kairosdb client

    Created on Thu Nov 03 23:21:42 2016

    @author:francesco.beneventi@unibo.it

    (c) 2017 University of Bologna, [Department of Electrical, Electronic and Information Engineering, DEI]

"""

import sys
import json
import gzip
import time
import urllib.request, urllib.error, urllib.parse
import http.client
import base64
import pickle
from io import StringIO
from cachetools import cached
from diskcache import FanoutCache
from functools import lru_cache

# import mmap
# import contextlib
# import tempfile

import zlib


DEBUG = False
d_cache = FanoutCache("examon-cache", shards=16, timeout=1)

def filtkey(self, *args, **kwargs):
    """Make mutable objects hashable.

    Used for complex dict args for cachetools.

    """
    return pickle.dumps(args, 1) + pickle.dumps(kwargs, 1)


class KairosDb(object):
    """Kairosdb REST client

    ...

    Parameters
    ----------
    host : str
        KairosDB server IP address
    port : str
        KairosDB server port. Default is 8083
    user : str
        username
    password : str
        password
    verbose : bool
        Print some extra output (useful for the debug). Default is True
    comp : str
        Enable Http compression. Default is 'gzip'
    proxy : bool
        Connect to the DB using an API gateway. Currently the client uses a
        Grafana server as a proxy for the db requests and users management.
        If 'True', the 'host', 'port', 'user' and 'password' arguments are
        the same of an existing Grafana account.

    """

    OUT_WIDTH = 40

    def __init__(self, host, port='8083', user=None, password=None, verbose=True, comp='gzip', proxy=False):
        """Create a Kairosdb connection object"""
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.verbose = verbose
        self.comp = comp
        self.proxy = proxy
        self.datasource_id = None
        self.url = "http://" + self.host + ":" + self.port
        if self.proxy:
            self.datasource_id = self.__get_datasource_id()


    def setup_kairosdb(self, cmd, method='POST'):
        """Build kairosdb API request"""

        url = self.url
        if self.proxy:
            url += '/api/datasources/proxy/' + str(self.datasource_id)
        url += "/api/v1/" + cmd
        return  self.build_req(url, method)


    def build_req(self, url, method):
        """Minimal REST client with basic auth"""

        req = urllib.request.Request(url)
        if method == 'POST':
            req.add_header('Content-Type', 'application/json')
        if self.comp == 'gzip':
            req.add_header('Accept-Encoding','gzip, deflate')
        req.add_header('Connection','close')

        if self.user is not None:
            if self.password is not None:
                if self.proxy:
                    base64string = base64.b64encode(('%s:%s' % (self.user, self.password)).encode()).decode()
                    req.add_header("Authorization", "Basic %s" % base64string)
                else:
                    password_manager = urllib.request.HTTPPasswordMgrWithDefaultRealm()
                    password_manager.add_password(None, url, self.user, self.password)
                    auth_manager = urllib.request.HTTPBasicAuthHandler(password_manager)
                    opener = urllib.request.build_opener(auth_manager)
                    urllib.request.install_opener(opener)
            else:
                self.__pprint('[HTTP]:', 'Please provide both username and password')
        if DEBUG:
            self.__pprint('[HTTP]:Method=',  method)
            self.__pprint('[HTTP]:Url=',  url)
        return req


    def send_req(self, req_api, json_data=None):
        """Build and send http request"""
        handler = None
        try:
            if json_data is not None:
                req = self.setup_kairosdb(req_api)
                t0 = time.time()
                handler = urllib.request.urlopen(req, json.dumps(json_data).encode("utf-8"))
                t1 = time.time()
            else:
                req = self.setup_kairosdb(req_api, method='GET')
                t0 = time.time()
                handler = urllib.request.urlopen(req)
                t1 = time.time()
        except urllib.error.HTTPError as e:
            self.__pprint('[HTTP]:HTTPError = ' , str(e.code))
            print(str(e.read()))
        except urllib.error.URLError as e:
            self.__pprint('[HTTP]:URLError = ' , str(e.reason))
        except http.client.HTTPException as e:
            self.__pprint('[HTTP]:HTTPException','')
        except Exception:
            import traceback
            self.__pprint('[HTTP]:generic exception: ' , traceback.format_exc())

        if handler:
            if self.verbose:
                self.print_http_ret(req_api, handler.getcode())
                #print "query time: %f" % (t1-t0)
                self.__pprint("query time", (t1-t0))
                print(handler.headers)

            if not DEBUG:
                if handler.info().get('Content-Encoding') == 'gzip':
                    # obj = StringIO(handler.read())
                    # dec = gzip.GzipFile(fileobj=obj)
                    # ret = dec.read()
                    # obj.close()
                    #
                    # with tempfile.TemporaryFile(mode='r+') as f_in:
                    #     with contextlib.closing(mmap.mmap(f_in.fileno(), 0)) as m:
                    #         m.write(handler.read())

                    return zlib.decompress(handler.read(), 16+zlib.MAX_WBITS)

                    #return ret
                else:
                    return handler.read()
            else:
                return {}
        else:
            raise ValueError('[HTTP]:Wrong HTTP response')

    def query_metrics(self, query):
        """Query metrics wrapper"""

        req_api = 'datapoints/query'
        return json.loads(self.send_req(req_api, query))

    def query_metricsnames(self, filter_kmetrics=True):
        """List of all metric names"""

        req_api = 'metricnames'
        res = json.loads(self.send_req(req_api))
        if filter_kmetrics:
            res['results'] = [x for x in res['results'] if 'kairosdb.' not in x]
        return res


    def query_tagnames(self):
        """List of all tag names"""

        req_api = 'tagnames'
        return json.loads(self.send_req(req_api))

    def query_tagvalues(self):
        """List of all tag values"""

        req_api = 'tagvalues'
        return json.loads(self.send_req(req_api))

    @cached(cache={}, key=filtkey)
    @d_cache.memoize()
    def __query_metrictags_resp(self, req_api, query):
        return json.loads(self.send_req(req_api, query))

    def query_metricstags(self, metric, tag=None, filt=None, cache=True):
        """Return tag values for a metric.

        Parameters
        ----------
        metric : str
            metric name
        tag : str
            tag key of the results values
        filt : dict
            use ``filt`` to narrow down the query (filtering by tag)
        cache : bool
            if ``True`` enable the caching of the metrics metadata (tags) to save
            db bandwidth during intensive usage. Default is ``True``.

        Examples
        --------
        ::

            # Get the values of the 'core' tag for the metric 'temp' of node 'node109'
            examon.query_metricstags('temp', 'core', filt={'node':['node109']})

        """
        req_api = 'datapoints/query/tags'

        query = {
               "start_absolute": 0,
               "cache_time": 0,
               "metrics": [
                   {
                       "name": metric
                   }
               ]
            }

        if filt is not None:
            query["metrics"][0]["tags"] = filt

        if cache:
            result = self.__query_metrictags_resp(req_api, query)
        else:
            result = json.loads(self.send_req(req_api, query))

        if tag is not None:
            for queries in result['queries']:
                for results in queries['results']:
                    try:
                        tag_values = results['tags'][tag]
                    except:
                        tag_values = []
                        continue

            return tag_values
        else:
            for queries in result['queries']:
                for results in queries['results']:
                    tag_names = list(results['tags'].keys())
            return tag_names

    def get_tagsfromquery(self, metric, tag):
        """Return tag values from the current query

        Parameters
        ----------
        metric : str
            metric name
        tag : str
            tag key of the results values

        """

        tag_values = []
        for queries in self.result['queries']:
            for results in queries['results']:
                if metric == results['name']:
                    tag_values = results['tags'][tag]

        return tag_values

    def __get_datasource_id(self):
        """Return grafana datasource id from datasource name"""

        datasource = 'kairosdb'
        req_api = self.url + '/api/datasources/id/' + datasource
        req = self.build_req(req_api,'GET')
        handler = urllib.request.urlopen(req)
        res = json.loads(handler.read())

        return res['id']

    def print_http_ret(self, caller, ret):
        """Print Http request status"""

        if str(ret) == '200':
            self.__pprint('[HTTP]:' + caller, 'OK')
        else:
            self.__pprint('[HTTP]:' + caller, 'FAILURE!')
            self.__pprint('[HTTP]:Return code:', ret)

    def __pprint(self, key, val):
        """Print key values data"""

        print('{:.<{width}s}{:.>{width}s}'.format(key, str(val), width=self.OUT_WIDTH))

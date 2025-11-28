

from collections import namedtuple

Query = namedtuple('Query','tstart tstop metrics tags groupby aggrby limit time_zone')


class QueryBuilder(object):
    """
        Kairosdb query builder
    """
    def __init__(self):
        self.query = Query(tstart=None,
                           tstop = None,
                           metrics = None,
                           tags = None,
                           groupby = None,
                           aggrby = None,
                           limit = None,
                           time_zone = 'Europe/Rome')
        self.metrics = []
        self.tags = {}
        self.aggregators = []
        self.groups = []
        self.required_fields = ['tstart', 'metrics']

    def setStart(self, tstart):
        self.query = self.query._replace(tstart = tstart)

    def setEnd(self, tstop):
        self.query = self.query._replace(tstop = tstop)

    def setLimit(self, limit):
        self.query = self.query._replace(limit = limit)

    def setTimezone(self, time_zone):
        self.query = self.query._replace(time_zone = time_zone)

    def addMetric(self, metric):
        self.__additem(metric, self.metrics)

    def addTags(self, tag):
        self.__additem(tag, self.tags)

    def addAggregator(self, aggr):
        self.__additem(aggr, self.aggregators)

    def addGroupby(self, groupby):
        self.__additem(groupby, self.groups)

    def __additem(self, x, xlist):
        if type(xlist) is list:
            if type(x) is list:
                xlist.extend(x)
            else:
                xlist.append(x)
        if type(xlist) is dict:
            if type(x) is dict:
                xlist.update(x)
            else:
                raise ValueError('%s type is dict' % x)

    def getQuery(self):
        if len(self.metrics) > 0:
            self.query = self.query._replace(metrics=self.metrics)
        if len(self.aggregators) > 0:
            self.query = self.query._replace(aggrby=self.aggregators)
        if len(self.groups) > 0:
            self.query = self.query._replace(groupby=self.groups)
        if len(self.tags) > 0:
            self.query = self.query._replace(tags=self.tags)
        for item in self.required_fields:
            if getattr(self.query, item) is None:
                raise ValueError('%s value is required' % item)
        return self.query

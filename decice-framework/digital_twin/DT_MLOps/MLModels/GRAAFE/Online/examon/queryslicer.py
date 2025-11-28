

import pytz
import datetime

class QuerySlicer(object):
    """
        Single Query Batching
    """
    def __init__(self):
        self.mills = {'seconds': 1000,
                           'minutes': 60*1000,
                           'hours': 60*60*1000,
                           'days': 24*60*60*1000,
                           'weeks': 7*24*60*60*1000,
                           'months': 30*24*60*60*1000,
                           'years': 12*30*24*60*60*1000}
        self.time_zone = None
        self.now = None

    def sliceQuery(self, query, step_millis):
        queries = []
        tstart = query.tstart
        tstop = query.tstop
        self.time_zone = query.time_zone
        self.now = self.get_utcnow()
        ranges = self.getRanges(self.get_millis(tstart), self.get_millis(tstop), step_millis)
        for k in ranges:
            temp_query = query._replace(tstart=k[0])
            temp_query = temp_query._replace(tstop=k[1])
            queries.append(temp_query)
        return queries

    def getRanges(self, tstart, tstop, step):

        ranges = []
        if (tstop - tstart) > step:
            a = list(range(tstart, tstop, step))
            for k in range(0,len(a)):
                if (a[k] + step) >= tstop:
                    ranges.append([a[k], tstop])
                else:
                    ranges.append([a[k],a[k+1]-1])
        else:
            ranges = [[tstart, tstop]]
        return ranges

    def get_utctmp(self, timestring=None):
        """
            To utc epoch (ms)
        """
        tz = pytz.timezone(self.time_zone)
        if timestring is not None:
            dt = datetime.datetime.strptime(timestring, "%d-%m-%Y %H:%M:%S")
        else:
            dt = datetime.datetime.now()
        dt_epoch = (tz.normalize(tz.localize(dt)).astimezone(pytz.utc) - datetime.datetime(1970,1,1).replace(tzinfo=pytz.UTC)).total_seconds()

        return int(dt_epoch*1000)

    def get_utcnow(self):
        """
            To utc epoch (ms)
        """
        return self.get_utctmp()
        #tz = pytz.timezone(self.time_zone)
        #dt = datetime.datetime.now()
        #dt_epoch = (tz.normalize(tz.localize(dt)).astimezone(pytz.utc) - datetime.datetime(1970,1,1).replace(tzinfo=pytz.UTC)).total_seconds()

        return int(dt_epoch*1000)

    def get_millis(self, t):
        milliseconds = 0
        #relative
        if type(t) is list:
            value = int(t[0])
            unit = t[1]
            milliseconds = self.now - int(value*self.mills[unit])
        #absolute
        elif type(t) is int:
            milliseconds = t
        #absolute-string
        elif type(t) is str:
             milliseconds = self.get_utctmp(t)
        elif t is None:
             milliseconds = self.now
        else:
            raise ValueError("time format error")

        return milliseconds

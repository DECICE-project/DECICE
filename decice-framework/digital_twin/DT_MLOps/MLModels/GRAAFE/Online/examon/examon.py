# -*- coding: utf-8 -*-
"""

    Examon python client

    Created on Thu Nov 03 23:21:42 2016

    @author:francesco.beneventi@unibo.it

    (c) 2017 University of Bologna, [Department of Electrical, Electronic and Information Engineering, DEI]

"""

import re
import json
import copy
import pytz
import datetime
import pandas as pd
from .kairosdb import KairosDb
from concurrent.futures import ThreadPoolExecutor, as_completed
from .querybuilder import QueryBuilder
from .jobsclient import JobsClient
from .executors import ExDask
from functools import reduce

THREADPOOL_WORKERS = 16

class ExamonQL(object):
    """Examon query language

    Provide an high level interface to data queries

    """
    def __init__(self, examon):
        self.ex = examon
        self.metric_list = None
        self.tag_list = None
        self.res_df_list = []
        self.qb = QueryBuilder()
        self.jc = JobsClient(self.ex.host, user=self.ex.user, password=self.ex.password, verbose=self.ex.verbose, comp=self.ex.comp)
        self.ds = ExDask(self.ex)
        self.get_tag_keys()

    def get_metrics_list(self):
        """Table of the metrics names (sensors) contained in the database"""

        if not self.metric_list:
            self.metric_list = {'name': self.ex.query_metricsnames()['results']}
        #print 'Number of sensors names: %d' % (len(self.metric_list))
        #return pd.DataFrame(self.metric_list)
        return self.metric_list

    def get_tag_keys(self, max_workers=THREADPOOL_WORKERS, cache=True):
        """Metrics tag keys table

        Each metric in the database comes with a set of tags (key;value) useful for
        filtering during queries. It is possible to obtain from the database all the
        possible tags (keys) associated to a specific metric. The following search
        will scan the entire database checking all the metrics tags.

        """

        if not self.tag_list:
            if not self.metric_list:
                self.get_metrics_list()
            self.tag_list = []
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_metrics = {executor.submit(self.ex.query_metricstags, m, None, None, cache): m for m in self.metric_list['name']}
                for future in as_completed(future_to_metrics):
                    row = {}
                    row['name'] = future_to_metrics[future]
                    row['tag keys'] = future.result()
                    if len(row['tag keys']):
                        self.tag_list.append(row)
        #return pd.DataFrame(self.tag_list)
        return self.tag_list


    def get_tag_values(self, metrics=None, tag=None, filt=None, max_workers=THREADPOOL_WORKERS, cache=True):
        """Filtered tag values

        Scan the db searching for tag values matching the filters conditions

        """

        if metrics==None:
            ml = self.get_metrics_list()
        else:
            ml = {}
            ml['name'] = metrics
        tag_values = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_metrics = {executor.submit(self.ex.query_metricstags, m, tag, filt, cache): m for m in ml['name']}
            for future in as_completed(future_to_metrics):
                row = {}
                row['name'] = future_to_metrics[future]
                row['tag key'] = tag
                row['tag values'] = future.result()
                if len(row['tag values']):
                    tag_values.append(row)
        #return pd.DataFrame(self.tag_list)
        return tag_values

    def get_metric_tag_values(self, metric):
        """All the possible values of all the tag keys of a given metric"""

        tag_values = []
        for tag_key in self.ex.query_metricstags(metric):
            row = {}
            row['name'] = metric
            row['tag key'] = tag_key
            row['tag values'] = self.ex.query_metricstags(metric, tag=tag_key)
            tag_values.append(row)
        #return pd.DataFrame(tag_values)
        return tag_values

    def get_metric_by_tag(self, tag_key, tag_value):
        """The list of the metrics having a given tag key/value pair"""

        metrics = []
        if not self.metric_list:
            self.get_metrics_list()
        for m in self.metric_list['name']:
            try:
                if tag_value in self.ex.query_metricstags(m, tag=tag_key):
                    metrics.append(m)
            except:
                continue
        #return pd.DataFrame({'name': metrics})
        return {'name': metrics}

    def get_all_tag_values(self, tag_key):
        """All the possible values of a given tag key"""

        values = []
        if not self.metric_list:
            self.get_metrics_list()
        for m in self.metric_list['name']:
            try:
                tag_values = self.ex.query_metricstags(m, tag=tag_key)
            except:
                continue
            values.extend(tag_values)
        unique_values = list(dict.fromkeys(values))
        #return pd.DataFrame({'tag values': unique_values})
        return {'tag values': unique_values}

    def DESCRIBE(self, metric=None, tag_key=None, tag_value=None, where=None):
        """High level db discovery function

        Return info about db metadata

        Parameters
        ----------
        metric : str
            metric name
        tag_key : str
            tag key
        tag_value : str
            tag value
        where : str
            filter condition. When not ``None``, it filters the results of the
            query: ``where='<tag_key>==<tag_value>[,<tag_value>,..]''``
            If separator character ``','`` is present in ``tag_value``, it must be
            escaped: ``'\,'``.

        Examples
        --------
        ::

            sq = ExamonQL(ex)

            # return name, tag keys table for all metrics
            sq.DESCRIBE().execute()

            # return metric name, tag_key, tag values for the provided metric
            sq.DESCRIBE(metric='<metric_name>').execute()

            # return tag values table for the given tag key
            sq.DESCRIBE(tag_key='<tag_key>').execute()

            # return metric name table for the tag key/value pair
            sq.DESCRIBE(tag_key ='<tag_key>', tag_value='<tag_value>').execute()

            # return metric name, tag_key, tag values for the provided tag key
            # matching the provided tag values
            sq.DESCRIBE(tag_key='<tag_key>', where='<tag_key>==<tag_value>[,<tag_value>,..]').execute()

            # return tag values for the provided tag key matching the provided
            # metric name and tag values
            sq.DESCRIBE(metric=['<metric_name>'], tag_key='<tag_key>', where='<tag_key>==<tag_value>[,<tag_value>,..]').execute()

        """

        if (metric==None) and (tag_key==None) and (tag_value==None) and (where==None):
            # return name,tag keys table for all metrics
            self.__add_result(pd.DataFrame(self.get_tag_keys()))
        elif (metric!=None) and (tag_key==None) and (tag_value==None) and (where==None):
            # return name, tag_key, tag values for the provided metric
            self.__add_result(pd.DataFrame(self.get_metric_tag_values(metric)))
        elif (metric==None) and (tag_key!=None) and (tag_value!=None) and (where==None):
            # return name table for the tag key/value pair
            self.__add_result(pd.DataFrame(self.get_metric_by_tag(tag_key, tag_value)))
        elif (metric==None) and (tag_key!=None) and (tag_value==None) and (where==None):
            # return tag values table for the given tag key
            self.__add_result(pd.DataFrame(self.get_all_tag_values(tag_key)))
        elif (tag_key!=None) and (where!=None):
            # return
            key, value = where.split('==')
            key = key.strip()
            if ',' in value:
                #value = value.split(',')
                value = [each.replace("\,",",") for each in re.split(r'(?<!\\),', value)]
                value = [x.strip() for x in value]
            else:
                value = [value.strip()]
            self.__add_result(pd.DataFrame(self.get_tag_values(metrics=metric, tag=tag_key, filt={key:value})))
        else:
            raise ValueError("Wrong Arguments")
        # set execution callback
        self.execute = self.__execute_meta
        return self

    def JOIN(self, how='inner'):
        """Join for the output tables of the DESCRIBE command

        Convenient method to join multiple DESCRIBE tables at once.

        Parameters
        ----------
        how : str
            * ``inner``: intersection (default)
            * ``outer``: union.

        """
        self.res_df_list = [reduce(lambda x, y: pd.merge(x, y, how=how), self.res_df_list)]
        # set execution callback
        #self.execute = self.__execute_meta
        return self

    def __add_result(self, df):
        self.res_df_list.append(df)

    def execute(self):
        """Execute the query"""
        pass

    def __execute_meta(self):
        res = copy.deepcopy(self.res_df_list)
        self.res_df_list = []
        return res[0]

    def __sanitize_args(self, args):
        args = list(args)
        if not len(args):
            return None
        args = [x.strip() for x in args]
        return args

    def SELECT(self, *args):
        """Select statement

        It defines the columns that must be present in the final table other
        than the implicit ``name``, ``timestamp`` and ``value`` (default columns).
        Under the hood, select enforces the groupby (tags) property of the standard
        db query.

        Parameters
        ----------
        args : str, optional
            Any valid tag key sequence: '<tag_key>'[,'<tag_key>',..].
            Using ``'*'`` as wildcard, the columns will be all the tags keys of
            the requested metric.

        Notes
        -----

        If no arguments are provided (equiv. to ``None``), the
        default behaviour is to return all tag key columns of the requested
        metric but without using the groupby operator in the query sento to the
        db server.

        """
        self.qb = QueryBuilder() # init
        args = self.__sanitize_args(args)
        if (args is None):
            pass
        elif ('*' in args):
            #args = self.ex.get_metric_tagnames(self.ex.query_metricsnames()['results'])
            self.qb.addGroupby('*')
        else:
            self.qb.addGroupby({'name':'tag', 'tags': args})
        self.execute = self.__execute_query
        return self

    def FROM(self, *args):
        """From statement

        It defines the metric names to query.

        Parameters
        ----------
        args : str
            At least one metric name, or a sequence.
            Use ``'*'`` as wildcard to request all metrics.

        """
        args = self.__sanitize_args(args)
        if (args is None):
            pass
        else:
            self.qb.addMetric(args)
        return self

    def WHERE(self, **kwargs):
        """Where statement

        It filters (by tag) the query.

        Parameters
        ----------
        kwargs : str
            One or multiple ``<tag_key>='<tag_value>[,<tag_value>,..]'`` arguments.
            If separator character ``','`` is present in ``tag_value``, it must be
            escaped: ``'\,'``.

        Examples
        --------
        ::

            data = sq.SELECT('*') \\
                .FROM('*') \\
                .WHERE(node='r169c11s04', plugin='nagios_pub', state='2') \\
                .TSTART(2,'months') \\
                .execute()

        """
        # sanitize
        tags = []
        for k,v in kwargs.items():
            key = k.strip()
            if key == 'time_zone':
                self.qb.setTimezone(v)
                continue
            if ',' in v:
                #value = v.split(',')
                value = [each.replace("\,",",") for each in re.split(r'(?<!\\),', v)]
                value = [x.strip() for x in value]
            else:
                value = [v.strip()]
            tags.append((key,value))
        tags = dict(tags)
        self.qb.addTags(tags)
        return self

    def TSTART(self, *args):
        """TSTART statement

        Defines the start time slice of the query

        Parameters
        ----------
        tstart : str, int
            can be one of the following:

            * relative: providing two arguments: ``<value>, '<unit>'``.
              ``value`` can be any int while ``unit`` can be 'milliseconds', 'seconds',
              'minutes', 'hours', 'days', 'weeks', 'months', and 'years'.
              The start time will be ``value`` ``units`` ago from now.
            * absolute date string: '%d-%m-%Y %H:%M:%S'
            * absolute epoch: int, milliseconds.

        """
        args = list(args)
        if len(args) == 2:
            self.qb.setStart(args)
        elif len(args) == 1:
            self.qb.setStart(args[0])
        else:
            raise ValueError('Wrong arguments number')
        return self

    def TSTOP(self, *args):
        """TSTOP statement

        Defines the stop time slice of the query

        Parameters
        ----------
        tstop : str, int
            can be one of the following:

            * relative: providing two arguments: ``<value>, '<unit>'``.
              ``value`` can be any int while ``unit`` can be 'milliseconds', 'seconds',
              'minutes', 'hours', 'days', 'weeks', 'months', and 'years'.
              The stop time will be ``value`` ``units`` ago from now.
            * absolute date string: '%d-%m-%Y %H:%M:%S'
            * absolute epoch: int, milliseconds.

        """
        args = list(args)
        if len(args) == 2:
            self.qb.setEnd(args)
        elif len(args) == 1:
            self.qb.setEnd(args[0])
        else:
            raise ValueError('Wrong arguments number')
        return self

    def LIMIT(self, limit):
        """Limit statement

        Limit the number of values returned by the query to the ``limit`` value

        Parameters
        ----------
        limit : int
            limit value

        """
        self.qb.setLimit(limit)
        return self

    def AGGRBY(self, name, align_sampling=True, align_start_time=False, \
               sampling_value=1, sampling_unit='minutes', **kwargs):
        """Aggregation statement

        Define the aggregators to apply at the query values (avg, sum, ..)

        Parameters
        ----------
        name : str
            one of: 'avg', 'dev', 'count', 'first', 'gaps', 'histogram', 'last', 'least_squares',
            'max', 'min', 'percentile', 'sum', 'diff', 'div', 'rate', 'sampler', 'scale', 'trim',
            'filter'.
            Check https://kairosdb.github.io/docs/build/html/restapi/Aggregators.html
            for the details.
        sampling_value : long
            size of the aggregation interval
        sampling_unit: str
            unit of the aggregation interval. Possible values: can be 'milliseconds',
            'seconds', 'minutes', 'hours', 'days', 'weeks', 'months', and 'years'.
        align_sampling : bool
            the aggregation interval is aligned based on the sampling size. Default ``True``
        align_start_time : bool
            aggragated data will have the timestamp matching the start of the interval.
            Default ``False``

        """
        if name:
            aggr = {
              "name": name,
              "align_sampling": align_sampling,
              "align_start_time": align_start_time,
              "sampling": {
                "value": sampling_value,
                "unit": sampling_unit
                }
            }
        else:
            raise ValueError('Wrong arguments number')

        if kwargs:
            for k,v in kwargs.items():
                aggr[k]=v

        self.qb.addAggregator(aggr)
        return self

    def __handle_wildcards(self):
        query = self.qb.getQuery()
        if query.metrics:
            if '*' in query.metrics:
                query = query._replace(metrics = self.metric_list['name'])
        if query.groupby:
            if '*' in query.groupby:
                groups = query.groupby
                tags = self.ex.get_metric_tagnames(query.metrics)
                groups = [{'name':'tag', 'tags': tags} if x=='*' else x for x in groups]
                query = query._replace(groupby = groups)
        return query

    def __execute_query(self):
        query = self.get_query()
        if set(query.metrics).issubset(self.jc.JOB_TABLES):  # check if a job table. TODO: better integration
            ret = self.jc.query_jobs(json.dumps(query._asdict()))
        else:
            ret = self.ex.query(*query)
        return ret

    def execute_async(self, batch_size=320000, npartitions=200, shuffle=False, **kwargs):
        query = self.get_query()
        ret = None
        if set(query.metrics).issubset(self.jc.JOB_TABLES):  # check if a job table. TODO: better integration
            ret = self.jc.query_jobs_async(query)
        else:
            #raise NotImplementedError
            columns = []
            for g in query.groupby:
                if g['name'] == 'tag':
                    columns.extend([x for x in g['tags']])
            #columns = [x for x in query.groupby['tags']]
            columns.append('name')
            meta = {a:'object' for a in columns}
            meta['timestamp'] = 'int64'
            meta['value'] = 'object'

            self.ds.q_slices = []
            df = self.ds.dask(**kwargs) \
                    .query(*query, batch_size=batch_size)
            if shuffle:
                df = df.shuffle()
            df = df.to_bag(npartitions=npartitions) \
                    .flatten() \
                    .to_dataframe(meta=meta) \
                    .persist()
            ret = df.categorize(columns=columns) \
                 .compute()
        return ret

    def get_query(self):
        """Return the query object obtained from the builder"""
        query = self.__handle_wildcards()
        if set(query.metrics).issubset(self.jc.JOB_TABLES):  # check if a job table. TODO: better integration
            query = query._replace(tstart = self.ex.get_utctmp(query.tstart,'UTC',format="%d-%m-%Y %H:%M:%S"))
            if query.tstop:
                query = query._replace(tstop = self.ex.get_utctmp(query.tstop,'UTC',format="%d-%m-%Y %H:%M:%S"))
        return query


class Examon(KairosDb):
    """Examon time-series interface"""

    def __init__(self, host, port='8083', user=None, password=None, verbose=True, comp='gzip', proxy=False):
        """Create an Examon object"""

        self.json_data = {}
        self.df_ts = pd.DataFrame()
        self.df_table = pd.DataFrame()
        self.dict_table = []
        self.verbose = verbose
        self.time_zone = None
        #self.dsl = ExamonDSL(self)
        super(Examon, self).__init__(host, port, user, password, verbose, comp, proxy)


    # def __getattr__(self, attr):
    #     return getattr(self.dsl, attr)

    def merge(self, df_list, interp=None, dropna=False):
        """Merge a list of dataframes.

        ...

        Parameters
        ----------
        df_list : list
            List of ``Pandas`` dataframes
        interp : str , optional
            The type of interpolation to apply. Default is ``None``.

            * ``time`` : linear interpolation using the time axis as reference.
            * ``zoh`` : zero-order hold. It fills the missing values using the
              last known value (see Pandas ``ffill``).

        dropna : bool, optional
            Remove the rows containing ``NaN`` elements. Default is False.

        Notes
        -----
        The behviour of this method is function of the ``df_list`` element shape.
        If the elements are of shape ``df_table`` they are concatenated.
        (see Pandas ``append``).
        If the elements are of shape ``df_ts`` it executes an outer join.


        """

        if type(df_list[0].index) is pd.core.indexes.datetimes.DatetimeIndex:
            self.df_ts = reduce(lambda x, y: pd.merge(x, y, how='outer', left_index=True, right_index=True), df_list)

            df2 = self.__nan_handler(interp, dropna)
            self.df_ts = df2.copy()

        if type(df_list[0].index) is pd.core.indexes.range.RangeIndex:
            self.df_table = reduce(lambda x, y: x.append(y, ignore_index=True), df_list)

        return copy.deepcopy(self)

    def to_series(self, columns=None, flat_index=False, interp=None, dropna=False):
        """Export query results to a time series table.

        ...

        Parameters
        ----------
        columns : list, optional
            list of column names to include in the resulting table. Default is
            all columns.
        flat_index : bool, optional
            * True : The resulting table has only one header row. The column names
              are in the format ``metric_name.tag=value.tag=value ...``
            * False : It returns a pandas dataframe with a ``MultiIndex`` type
              header.
        interp : str , optional
            The type of interpolation to apply. Default is ``None``.

            * ``time`` : linear interpolation using the time axis as reference.
            * ``zoh`` : zero-order hold. It fills the missing values using the
              last known value (see Pandas ``ffill``).

        dropna : bool, optional
            Remove the rows containing ``NaN`` elements. Default is False.

        """

        if columns is None:
            columns = ["name"]
            gp_tags = self.get_groupby_tagnames()
            if gp_tags:
                columns.extend(gp_tags)

        self.df_ts = pd.pivot_table(self.df_table,index=["timestamp"], columns=columns, values="value", aggfunc="first")

        if len(columns) > 1:
            if flat_index is True:
                self.df_ts.columns = self.__to_labels(list(self.df_ts.columns.names), self.df_ts.columns.values.tolist())

        df2 = self.__nan_handler(interp, dropna)
        self.df_ts = df2.copy()

        return self

    # def to_table(self):
    #     """Export query results to a generic table (dataframe)
    #
    #     ...
    #
    #     """
    #     self.to_dict()
    #     if len(self.dict_table):
    #         self.df_table = pd.DataFrame(self.dict_table)
    #         self.df_table['timestamp'] = pd.to_datetime(self.df_table['timestamp'], unit='ms') \
    #                                                 .dt.tz_localize(tz='UTC')  \
    #                                                 .dt.tz_convert(tz=self.time_zone)
    #         # --------- use categoricals
    #         #cat = list(self.df_table.columns)
    #         #cat.remove(u'timestamp')
    #         #cat.remove(u'value')
    #         #for col in cat:
    #         #    self.df_table[col] = self.df_table[col].astype('category')
    #         # --------------------------
    #     else:
    #         self.df_table = pd.DataFrame()
    #
    #     return self

    def to_table(self):
        """Export query results to a generic table (dataframe)

        ...

        """

        self.df_table = pd.DataFrame(self.to_dict())
        if len(self.df_table):
            self.df_table['timestamp'] = pd.to_datetime(self.df_table['timestamp'], unit='ms') \
                                                    .dt.tz_localize(tz='UTC')  \
                                                    .dt.tz_convert(tz=self.time_zone)
            # --------- use categoricals
            #cat = list(self.df_table.columns)
            #cat.remove(u'timestamp')
            #cat.remove(u'value')
            #for col in cat:
            #    self.df_table[col] = self.df_table[col].astype('category')
            # --------------------------

        return self

    # def to_dict(self):
    #     """
    #         Export query results to list of dict (rows) : Keep only 'group_by' tags
    #     """
    #
    #     self.dict_table = []
    #     for queries in self.json_data['queries']:
    #         if int(queries['sample_size']) > 0:
    #             for results in queries['results']:
    #                 row = {}
    #                 for g in results['group_by']:
    #                     if g['name']=='tag':
    #                         row = {k:v for k,v in g['group'].iteritems()}
    #                         break
    #                 if len(row) == 0:
    #                     row = {k:v[0] for k,v in results['tags'].iteritems()}
    #                 row_tv = [{'timestamp': t[0], 'value': t[1], 'name': results['name']} for t in results['values']]
    #                 for t in row_tv:
    #                     t.update(row)
    #                 self.dict_table.extend(row_tv)
    #                 results['values'] = None  #clear vectors
    #
    #     return self

    def to_dict(self):
        """
            Export query results to list of dict (rows) : Keep only 'group_by' tags
        """

        for queries in self.json_data['queries']:
            if int(queries['sample_size']) > 0:
                for results in queries['results']:
                    row = {}
                    for g in results['group_by']:
                        if g['name']=='tag':
                            row = {k:v for k,v in g['group'].items()}
                            break
                    if len(row) == 0:
                        row = {k:v[0] for k,v in results['tags'].items()}
                    # row_tv = [{'timestamp': t[0], 'value': t[1], 'name': results['name']} for t in results['values']]
                    # results['values'] = None  #clear vectors
                    row_tv = ({'timestamp': t[0], 'value': t[1], 'name': results['name']} for t in results['values'])
                    for t in row_tv:
                        t.update(row)
                        yield t
                    results['values'] = None  #clear vectors


    def to_excel(self, filename, interp=None, dropna=False, epoch=False):
        """Export to excel (deprecated)."""

        dt_format = 'dd-mm-yy hh:mm:ss.000'
        writer = pd.ExcelWriter(filename, engine='xlsxwriter', datetime_format=dt_format)

        df2 = self.__nan_handler(interp, dropna)

        if epoch is True:
            df2.set_index(self.df_ts.index.astype('int64')).to_excel(writer, sheet_name='Sheet1')
        else:
            df2.to_excel(writer, sheet_name='Sheet1')

        writer.save()

    def to_csv(self, filename, sep=';', decimal='.', interp=None, dropna=False, epoch=False, shape='ts', **kwargs):
        """ Export to csv.

        Convenient method to export the query results to a csv file.

        Parameters
        ----------
        filename : str
            Path to the output file location.
        sep : str, optional
            Column separator. Default is ';'
        decimal : str, optional
            Decimal format separator. Default is '.'
        interp : str , optional
            The type of interpolation to apply. Default is ``None``.

            * ``time`` : linear interpolation using the time axis as reference.
            * ``zoh`` : zero-order hold. It fills the missing values using the
              last known value (see Pandas ``ffill``).

        dropna : bool, optional
            Remove the rows containing ``NaN`` elements. Default is ``False``.
        epoch : bool, optional
            ``True`` if the timestamp format should be in the epoch format (ns)
            Default is ``False``
        shape : str, optional
            The layout of the resulting table.

            * 'ts' : time series format, ``df_ts``
            * 'df' : generic format, ``df_table``

        kwargs : optional
            Extra argument passed to pandas ``to_csv``

        """

        dt_format = "%d-%m-%Y %H:%M:%S"
        flt_format = '%.12f'

        if shape == 'ts':
            df2 = self.__nan_handler(interp, dropna).copy()

            if epoch is True:
                df2.set_index(self.df_ts.index.astype('int64'), inplace=True)
            df2.to_csv(filename, sep=sep, decimal=decimal, float_format=flt_format, **kwargs)

        elif shape == 'table':
            df2 = self.df_table.copy()

            if epoch is True:
                df2['timestamp'] = df2['timestamp'].astype('int64')
            df2.to_csv(filename, sep=sep, decimal=decimal, float_format=flt_format, **kwargs)

    def get_tags(self):
        """Return single metric, non grouped queries result, tags

        Get the tags (keys) from the ``tags`` field of the query response.

        """
        ret = []
        for queries in self.json_data['queries']:
            if int(queries['sample_size']) > 0:
                for results in queries['results']:
                    ret =  list(results['tags'].keys())
                    break
        return ret

    def get_groupby_tagnames(self):
        """Return single metric, groupby tags names (list)

        Get the tag names (keys) from the ``group`` field of the query response.

        """
        ret = []
        for queries in self.json_data['queries']:
            if int(queries['sample_size']) > 0:
                for results in queries['results']:
                    for g in results['group_by']:
                        if g['name']=='tag':
                            ret =  list(g['group'].keys())
                            break
        return ret

    def get_values(self):
        """Return single metric, non grouped queries result, values (list)

        (Deprecated)

        """
        x,y = list(zip(*self.json_data['queries'][0]['results'][0]['values']))  #get x,y values for each metric
        return y

    def get_utctmp(self, timestring, time_zone, format="%d-%m-%Y %H:%M:%S"):
        """Time string to utc epoch (ms)

        Parameters
        ----------
        timestring : str
            date in the  "%d-%m-%Y %H:%M:%S" format.
        time_zone : str
            timezone of the ``timestring`` date.
        format : str
            override input date format
        """
        tz = pytz.timezone(time_zone)
        dt = datetime.datetime.strptime(timestring, format)
        dt_epoch = (tz.normalize(tz.localize(dt)).astimezone(pytz.utc) - datetime.datetime(1970,1,1).replace(tzinfo=pytz.UTC)).total_seconds()

        return int(dt_epoch*1000)

    def get_metric_tagnames(self, metrics, max_workers=THREADPOOL_WORKERS, cache=True):
        """Get tag names that relate only to the provided metrics """

        taglist = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_metrics = {executor.submit(self.query_metricstags, m, None, None, cache): m for m in metrics}
            for future in as_completed(future_to_metrics):
                tags = future.result()
                if len(tags):
                    taglist.extend(tags)
        return list(dict.fromkeys(taglist))

    def __to_labels(self, names, values):

        labels_dic_list = [dict(list(zip(names, val))) for val in values]

        labels_list = []
        for lbl in labels_dic_list:
            lab = lbl['name']
            for k,v in lbl.items():
                if k == 'name':
                    continue
                lab += '.%s=%s' % (k,v)
            labels_list.append(lab)

        return labels_list

    def __nan_handler(self, interp, dropna):
        # FIXME: modify to do fill operations "inplace"
        if interp is not None:
            if interp == 'time':
                if dropna is True:
                    df2 = self.df_ts.interpolate(method='time').dropna(axis=0, how='any')
                else:
                    df2 = self.df_ts.interpolate(method='time')
            elif interp == 'zoh':
                if dropna is True:
                    df2 = self.df_ts.fillna(method='ffill').dropna(axis=0, how='any')
                else:
                    df2 = self.df_ts.fillna(method='ffill')
        else:
            if dropna is True:
                df2 = self.df_ts.dropna(axis=0, how='any')
            else:
                df2 = self.df_ts

        return df2

    def query_tojson(self, tstart, tstop, metric_names, tags=None, groupby=None, aggrby=None, limit=None, time_zone='Europe/Rome'):
        """Query builder"""

        def __additem(x, xlist):
            if type(x) is list:
                xlist.extend(x)
            else:
                xlist.append(x)
        query = {}
        query['cache_time'] = 0
        query['time_zone'] = time_zone
        self.time_zone = time_zone
        query['metrics'] = []

        # wildcards handler
        if metric_names == ['*']:
            metric_names = self.query_metricsnames()['results']
            if groupby is None:
                groupby = {'name':'tag', 'tags': self.query_tagnames()['results']}
                # taglist = []
                # for m in metric_names:
                #     t = self.query_metricstags(m)
                #     taglist.extend(t)
                # groupby = {'name':'tag', 'tags': list(dict.fromkeys(taglist))}

        for metrics in metric_names:
            metric = {}
            metric['name'] = metrics


            if limit is not None:
                metric['limit'] = int(limit)

            if tags is not None:
                metric['tags'] = tags
            else:
                metric['tags'] = {}

            if groupby is not None:
                metric['group_by'] = []
                __additem(groupby, metric['group_by'])

            if aggrby is not None:
                metric['aggregators'] = []
                __additem(aggrby, metric['aggregators'])

            if tstart is not None:
                if type(tstart) is list:
                    query['start_relative'] = {}
                    query['start_relative']['value'] = tstart[0]
                    query['start_relative']['unit'] = tstart[1]
                elif type(tstart) in [int, int]:
                    query['start_absolute'] = tstart
                elif type(tstart) is str:
                    query['start_absolute'] = self.get_utctmp(tstart, time_zone)
                else:
                    print("tstart format error")
            else:
                print("tstart parameter is required")

            if tstop is not None:
                if type(tstop) is list:
                    query['end_relative'] = {}
                    query['end_relative']['value'] = tstop[0]
                    query['end_relative']['unit'] = tstop[1]
                elif type(tstop) in [int, int]:
                    query['end_absolute'] = tstop
                elif type(tstop) is str:
                    query['end_absolute'] = self.get_utctmp(tstop, time_zone)
                else:
                    print("tstop format error")

            query['metrics'].append(metric)

        if self.verbose:
            print('{:=>{width}s}'.format('=', width=2*self.OUT_WIDTH))
            print('[Query Builder]:Generated query:')
            print('{:=>{width}s}'.format('=', width=2*self.OUT_WIDTH))
            print(json.dumps(query, indent=4))
            print('{:=>{width}s}'.format('=', width=2*self.OUT_WIDTH))
        return query

    def query(self, tstart, tstop, metric_names, tags=None, groupby=None, aggrby=None, limit=None, time_zone='Europe/Rome'):
        """Kairosdb query

        Build and execute a query on KairosDB

        Parameters
        ----------
        tstart : list, long, str
            Time indicating the oldest value requested by the query.
            Can be of different formats:

            * list : [<value> ,<"units">] where ``units`` can be 'seconds', 'minutes', 'hours',
              'days', 'months', 'years'.
            * long : a ``long`` integer representing the epoch time (milliseconds)
            * str : a date string in the ``"%d-%m-%Y %H:%M:%S"`` format.

        tstop : list, long, str
            Time indicating the most recent value requested by the query
            Can be of different formats (see ``tstart``)
        metric_names : list
            List of metrics names
        tags : dict, optional
            Tags definition in the KairosDB format: ``{<Tag_name>:[list of values],...}``
        groupby : dict, optional
            Groups definition  in the kairosDB format::

                {"name": <grouper name>,
                <grouper paramenters name>:<grouper paramenters values>,
                ...}

        aggrby : dict, optional
            Aggregators definition in the KairosDB format::

                {"name": <aggr_type>,
                 "align_sampling": <bool>,
                 "sampling": {
                            "value": <"val">,
                            "unit": <"time units">
                    },
                 "align_start_time": <bool>
                }

        limit : int, optional
            The number of samples effectively returned by the query. Default is
            None
        time_zone : str, optional
            timezone of the ``tstart``/``tstop`` dates.

        Returns
        -------
        <examon.examon.Examon>
            An examon object with the query results in two formats:

            * raw : as returned by KairosDB in ``examon.json_data``
            * Pandas dataframe : generic table format in ``examon.df_table``

        Notes
        -----

        REF: https://kairosdb.github.io/docs/build/html/restapi/QueryMetrics.html

        """

        query_json = self.query_tojson(tstart, tstop, metric_names, tags, groupby, aggrby, limit, time_zone)
        return self.exec_query(query_json)

    def exec_query(self, query_json):
        """Execute query"""
        self.json_data = self.query_metrics(query_json)
        self.to_table()
        return copy.deepcopy(self)   # FIXME: <<<<<<<<<<<<<<<<<<<< TODO return self: build a new object at every query (modfify this in doc)

    def query_batch(self, tstart, tstop, metric_names, tags=None, groupby=None, aggrby=None, limit=None, time_zone='Europe/Rome'):
        """Query for batch frameworks"""
        query_json = self.query_tojson(tstart, tstop, metric_names, tags, groupby, aggrby, limit, time_zone)
        return self.exec_query_batch(query_json)

    def exec_query_batch(self, query_json):
        """Execute query for batch frameworks"""
        self.json_data = self.query_metrics(query_json)
        #self.to_dict()
        return self

#
# Alias for the db Client semantics
#
#  from examon import examon
#  client = examon.Client(SERVER)
#
Client = Examon

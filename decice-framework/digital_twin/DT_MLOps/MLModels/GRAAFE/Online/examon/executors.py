"""

    Examon - Big data tools interface

    Created on 05/07/2019, 8:22:22 PM

    @author:francesco.beneventi@unibo.it

    (c) 2017 University of Bologna, [Department of Electrical, Electronic and Information Engineering, DEI]

"""

from .querybuilder import QueryBuilder
from .queryslicer import QuerySlicer
from random import shuffle


# spark context
sc = None
# dask cluster
client = None


class ExBase(object):

    def __init__(self, ex):
        self.ex = ex
        self.q_slices = []

    def query(self, tstart, tstop, metric_names, tags=None, groupby=None, aggrby=None, limit=None, time_zone='Europe/Rome', batch_size=30*60*1000):
        query = QueryBuilder()
        query.setStart(tstart)
        query.setEnd(tstop)
        query.addMetric(metric_names)
        if tags is not None: # put all metric tags by default
            query.addTags(tags)
        if groupby is None: # groupby all
            taglist = self.ex.get_metric_tagnames(metric_names)
            query.addGroupby({'name':'tag', 'tags': taglist})
        else:
            query.addGroupby(groupby)
        if aggrby is not None:
            query.addAggregator(aggrby)
        query.setLimit(limit)
        query.setTimezone(time_zone)  #client timezone: where this code is executed

        print(query.getQuery())
        # add query to batch
        qs = QuerySlicer()
        self.q_slices.extend(qs.sliceQuery(query.getQuery(), batch_size))

        return self

    def shuffle(self):
        shuffle(self.q_slices)
        return self


class ExSpark(ExBase):

    def __init__(self, ex):
        from pyspark.sql import Row
        self.Row = Row
        super(ExSpark, self).__init__(ex)

    def spark(self, spark_context):
        global sc
        sc = spark_context
        return self

    def to_rdd(self, npartitions=None, repartition=None):
        global sc
        if npartitions is not None:
            queries_rdd = sc.parallelize(self.q_slices, npartitions)
        else:
            queries_rdd = sc.parallelize(self.q_slices)
        results_rdd = queries_rdd.flatMap(self.kdb_query_to_rows)
        if repartition is not None:
            results_rdd = results_rdd.repartition(repartition)
        return results_rdd

    def kdb_query_to_rows(self, q):
        ret = self.ex.query_batch(*q)
        return (self.Row(**{k: None if not v else v for k, v in list(x.items()) }) for x in ret.to_dict())


class ExDask(ExBase):

    def __init__(self, ex):
        import dask.bag as db
        self.db = db
        #self.client = None
        super(ExDask, self).__init__(ex)

    def dask(self, dask_client=None, **client_kwargs):
        global client
        
        if client is None:
            if dask_client is None:
                from dask.distributed import Client
                client = Client(**client_kwargs)
            else:
                client = dask_client
        #client.cluster
        return self

    def close(self):
        global client
        if client is not None:
            client.close()
            client = None

    def restart(self):
        global client
        if client is not None:
            client.restart()

    def to_bag(self, npartitions=None, repartition=None):
        if npartitions is not None:
            queries_bag = self.db.from_sequence(self.q_slices, npartitions=npartitions)
        else:
            queries_bag = self.db.from_sequence(self.q_slices)
        results_bag = queries_bag.map(self.kdb_query_to_rows)
        if repartition is not None:
            results_bag = results_bag.repartition(repartition)
        return results_bag

    def to_df(self, npartitions=None, repartition=None):
        df = self.to_bag(npartitions=npartitions, repartition=repartition).flatten().to_dataframe()
        return df

    def kdb_query_to_rows(self, q):
        ret = self.ex.query_batch(*q)
        return ret.to_dict()

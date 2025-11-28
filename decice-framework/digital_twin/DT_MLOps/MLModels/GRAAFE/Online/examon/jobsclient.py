# -*- coding: utf-8 -*-
"""

    Batch scheduler data client (db)

    Created on 2/10/2019, 12:15:26 PM

    @author:francesco.beneventi@unibo.it

    (c) 2017 University of Bologna, [Department of Electrical, Electronic and Information Engineering, DEI]

"""

import json
from .kairosdb import KairosDb
from concurrent.futures import ThreadPoolExecutor, as_completed
from .queryslicer import QuerySlicer
from random import shuffle


class JobsClient(KairosDb):
    """Batch scheduler data client

    Temporary interface to jobs data.
    Enable the examon client to fetch data from the job tables
    currently stored in C*.

    """

    def __init__(self, host, port='5000', user=None, password=None, verbose=False, comp='gzip', proxy=False):
        self.JOB_TABLES = {'job_info_galileo','job_info_marconi'}  # TODO: make this dynamic
        self.qs = QuerySlicer()
        self.q_slices = []
        super(JobsClient, self).__init__(host, port, user, password, verbose, comp, proxy)

    def query_jobs(self, query):
        """Send a query to the examon server

        ...

        Parameters
        ----------
        query : json
            The query is a Query object serialized to json.

        Returns
        -------
            A serialized (json) Pandas dataframe

        """
        req_api = 'examon/jobs/query'
        return json.loads(self.send_req(req_api, query))

    def query_jobs_async(self, query, max_worker=16, batch_size=12*60*60*1000):
        """Async query for the examon server

        ...

        """
        queries = []
        queries.extend(self.qs.sliceQuery(query, batch_size))

        shuffle(self.q_slices)
        
        results = []
        with ThreadPoolExecutor(max_workers=max_worker) as executor:
            futures = [executor.submit(self.query_jobs, json.dumps(q._asdict())) for q in queries]
            for future in as_completed(futures):
                results.extend(json.loads(future.result()))

        return json.dumps(results)

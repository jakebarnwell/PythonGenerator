import aws
import tweepy
import sys
import random
import numpy as np
import time
import thread
import datetime

S3_LINK_HOLDER = '###S3###'

class Crawl_Controller:

    def assign_task(self, crawler_id, OSN, attributes, parameter):
        """
        Assign the task with the following format:

        1. crawler_id : which crawler to perform the retrieval tasks.
        2. OSN (Online Social Network) : which OSN will the crawler use, typically it means that whether to use Twitter_API, Facebook_API or others.
        3. attributes : Inside the API, which attribute that the crawler would like to retrieve. It is like a action to retrieve or perform the sampling algorithm on it.
        4. *parameters : Parameters for attributes actions.
        """
        task_message = [crawler_id] + [OSN] + [attributes] + [parameter]
        messgae = ' '.join(task_message)
        aws.write_crawler_queue(messgae)

    def geweke(self, x, precision=0.1, first=0.1, last=0.5, intervals=20):
        """Return z-scores for convergence diagnostics.

        Compare the mean of the first % of series with the mean of the last % of
        series. x is divided into a number of segments for which this difference is
        computed. If the series is converged, this score should oscillate between
        -1 and 1.

        Parameters
        ----------
        x : array-like
        The trace of some stochastic parameter.
        first : float
        The fraction of series at the beginning of the trace.
        last : float
        The fraction of series at the end to be compared with the section
        at the beginning.
        intervals : int
        The number of segments.

        Returns
        -------
        scores : list [[]]
        Return a list of [i, score], where i is the starting index for each
        interval and score the Geweke score on the interval.

        Notes
        -----

        The Geweke score on some series x is computed by:

          .. math:: \frac{E[x_s] - E[x_e]}{\sqrt{V[x_s] + V[x_e]}}

        where :math:`E` stands for the mean, :math:`V` the variance,
        :math:`x_s` a section at the start of the series and
        :math:`x_e` a section at the end of the series.

        References
        ----------
        Geweke (1992)
        """
        x = np.array(x)

        NOT_CONVERGED = -1

        if np.rank(x)>1:
            return [self.geweke(y, precision,  first, last, intervals) for y in np.transpose(x)]

        # Filter out invalid intervals
        if first + last >= 1:
            raise "Invalid intervals for Geweke convergence analysis",(first,last)

        # Last index value
        end = len(x) - 1

        # Calculate starting indices
        sindices = np.arange(0, end/2, step = int((end / 2) / (intervals-1)))

        # Loop over start indices
        for start in sindices:

            # Calculate slices
            first_slice = x[start : start + int(first * (end - start))]
            last_slice = x[int(end - last * (end - start)):]

            z = (first_slice.mean() - last_slice.mean())
            z /= np.sqrt(first_slice.std()**2 + last_slice.std()**2)

            if abs(z) < precision:
                return start

        return NOT_CONVERGED

    def generate_initial_node(self, OSN):
        """generate the initial node for specific online social networks. """
        if OSN == 'Twitter':
            return '110347344'
        elif OSN == 'Facebook':
            return None
            pass

    def get_neighbors(self, OSN, user_id, neighbor_name='friends'):
        """get_neighbors is a universal scheme for random walk based sampling algorithm.

        By definition, 'Neighbors' can be defined differently in different OSNs. For example, in undirected OSN like Facebook, neighbors can be intuitively defined as the friends of one user, while in directed OSN such as Twitter, neighbors can be defined as the union or intersection of the users' followers and followings.
        We denote the neighbors in a [neighbor list].

        It should complete the following steps.
        1. Check the cache (SimpleDB as the cache) to see if the [neighbor list] exists or not.
        2. If exists, check if it is in SimpleDB or S3. Then return the neighbor list as a list.
        3. If it does not exist in the cache, assign an task to let the crawlers do the crawlling work. Peorically check the cache until the cache does have the [neighbor list]."""

        meta_sdb = aws.get_simpledb(OSN.lower() + '-meta')
        meta_s3 = aws.get_s3('wisesoc.' + OSN.lower() + '.meta')

        # Check the cache
        item_name = str(user_id)

        MESSAGE_SEND = 0

        while 1:
            neighbors = aws.read_simpledb(meta_sdb, item_name)
            if neighbors is not None:
                if neighbors[neighbor_name] == S3_LINK_HOLDER:
                    while 1:
                        try:
                            s3_result = eval(aws.read_s3(meta_s3, item_name)[neighbor_name])
                            break
                        except:
                            time.sleep(0.1)
                            continue
                    return s3_result

                elif neighbors[neighbor_name] == 'None':
                    return None
                else:
                    return eval(neighbors[neighbor_name])
            else:
                if MESSAGE_SEND == 0:
                    print 'not hit, wait for %s' % (item_name)
                    self.assign_task('c_1', OSN + '_Crawler', 'get_' + neighbor_name, item_name)
                    MESSAGE_SEND = 1

    def simple_random_walk(self,
                s_id='s_0',
                OSN='Twitter',
                fixQuery=100,
                burnBound=50,
                geweke_threshold=0.1):
            """Simple Random Walk start from a specific initial node, uniformly pick the node's neighbor as the next step recursively.

            Note that there are a few parameters:
                1. fixQuery is to limit the query cost.
                2. burnBound is used by Geweke Diagnostic Method.
                3. geweke_threshold is also the threshold for z-statistics.
            """

            #Record state of the random walk.
            srw_s3 = aws.create_s3('wisesoc.' + OSN.lower() + '.srw')

            #Initial Node should be a string of id. For example '123456'.
            initial_node = self.generate_initial_node(OSN)
            node_v = initial_node

            neighbors_v = self.get_neighbors(OSN, node_v)
            monitor_value = []
            monitor_nodes= []
            burnStep = -1

            while True:
                #Geweke Diagnostic for Convergence
                #monitor_value.append(1.0 / float(len(neighbors_v)))
                monitor_value.append(len(neighbors_v))
                monitor_nodes.append(node_v)

                #record the monitor_value and monitor_nodes to S3
                aws.write_s3(srw_s3, s_id + 'monitor_value', str(monitor_value))
                aws.write_s3(srw_s3, s_id + 'monitor_nodes', str(monitor_nodes))

                step = len(monitor_value)

                if step > burnBound:
                    burnStep = self.geweke(monitor_value, geweke_threshold)

                if burnStep >= 0:
                    record_step = burnStep
                    record_samples = monitor_nodes[burnStep+1:]
                    record_samples_deg = monitor_value[burnStep+1:]
                    break
                else:
                    while 1:
                        node_v = neighbors_v[random.randint(0, len(neighbors_v)-1)]
                        print 's_id: ', s_id
                        tmp_neighbors = self.get_neighbors(OSN, node_v)
                        len_tmp_neighbors = len(tmp_neighbors) if tmp_neighbors else 0
                        if len_tmp_neighbors >=2 :
                            neighbors_v = tmp_neighbors
                            break
                    continue


            logOutput = { 'OSN': OSN, \
                         'record_trace': monitor_nodes, \
                         'record_step': record_step, \
                         'record_samples_deg': record_samples_deg, \
                         'record_samples' : record_samples}

            aws.write_s3(srw_s3, s_id + 'logOutput' + str(datetime.datetime.now())[:-7], str(logOutput))
            print "Write to log. ", s_id

            return logOutput

    def multithread_simple_random_walk(self, num_threads=10):
        """Issue multiple random walks."""
        for i in range(num_threads):
            #thread.start_new_thread(print, 's_'+str(i), *args, **kargs)
            s_id = 's_' + str(i)
            thread.start_new_thread(self.simple_random_walk, (s_id,))
            time.sleep(0.1)

        while 1:
            pass


class Crawler:

    STATUS_IDLE = -1
    STATUS_OFF = 0
    STATUS_ON = 1
    STATUS_BUSY = 2

    SDB_LIMIT = 1000

    def __init__(self, crawler_id):

        """
        Crawler_id are expressed as the sequence of c_1, c_2, c_3, ... etc
        Crawler Resources are the name set of all those online social networks plus the string '_Crawler'
        """
        self.crawler_id = crawler_id

        # Crawler Resources
        self.crawler_resources = ['Twitter_Crawler', 'Facebook_Crawler', 'GooglePlus_Crawler', 'LinkedIn_Crawler']
        # Crawler Supported APIs
        self.crawler_actions = ['get_followers', 'get_followings', 'get_friends', 'get_info', 'get_specifics']

        self.status = self.STATUS_ON

    def reset(self):
        """Reset the instance to complete the next task"""
        self.task = None
        self.instance = None
        self.results = None
        self.message = None

    def parse_sqs(self):
        """Tasks are messages with format 'crawler_id api get_attributes parameters' """
        task_message = aws.read_crawler_queue()
        if task_message is None:
            self.task = None
        else:
            task = task_message.get_body().split()

            # Varification of the task_message
            try:
                assert task[1] in self.crawler_resources
                assert task[2] in self.crawler_actions
                assert task[3] is not None
                assert eval(task[3])
            except (AssertionError, IndexError, SyntaxError):
                aws.delete_crawler_queue(task_message)
                self.task = None
                return None
            self.task = task
            self.message = task_message

    def generate_instance(self, *keys):
        """task is the message retrived."""
        instance = eval(self.task[1])()
        instance.set_keys(*keys)
        self.instance = instance

    def retrieve(self):
        """Retrieve data from the remote online social networks.
        Confirm the self.task first to see if the crawler has been driven by the API in crawler_resources. Store the results in self.results

        self.results is a dict format. The keys of the results are from the self.task[2]

        E.g.
        self.results = {'friends': ['123456', '234567']}"""

        assert self.task[1] in self.crawler_resources
        results = None
        #check crawler_id
        self.status = self.STATUS_BUSY
        try:
            results = getattr(self.instance, self.task[2])(*self.task[3:])
        except tweepy.TweepError:
            results = None

        aws.delete_crawler_queue(self.message)
        self.status = self.STATUS_ON

        self.results = {self.task[2].split('_')[1]:str(results)}
        self.results_size = sys.getsizeof(str(results))

    def store(self):
        """Store to SimpleDB first, if it exceed the size limit of 1024bytes, then go to S3 storage."""

        # SimpleDB Domain Name Example: twitter-meta, twitter-rw
        self.meta_sdb = aws.get_simpledb(self.task[1].split('_')[0].lower() + '-meta')
        self.meta_s3 = aws.get_s3('wisesoc.' + self.task[1].split('_')[0].lower() + '.meta')
        store_key = self.task[3]
        if self.results_size <= self.SDB_LIMIT:
            aws.write_simpledb(self.meta_sdb, store_key, self.results)
        else:
            aws.write_simpledb(self.meta_sdb, store_key, {self.task[2].split('_')[1]: S3_LINK_HOLDER})
            aws.write_s3(self.meta_s3, store_key, self.results)
        print 'saved: ', self.crawler_id, self.task

    def verify_store_data(self):
        """docstring for verify_store_data"""
        store_key = self.task[3]
        print 'verifying : ', self.task
        if self.results_size <= self.SDB_LIMIT:
            print 'Stored in SimpleDB'
            assert str(self.results[self.task[2].split('_')[1]]) == aws.read_simpledb(self.meta_sdb, store_key)[self.task[2].split('_')[1]]
        else:
            print 'Stored in S3'
            assert aws.read_simpledb(self.meta_sdb, store_key)[self.task[2].split('_')[1]] == S3_LINK_HOLDER
            assert aws.read_s3(self.meta_s3, store_key)[self.task[2].split('_')[1]] is not None


class Twitter_Crawler:

    def __init__(self):
        self.api = None

    def set_keys(self, consumer_key=None, consumer_secret=None, access_token=None, access_token_secret=None):
        auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
        auth.set_access_token(access_token, access_token_secret)
        self.api = tweepy.API(auth)

    def get_friends(self, *args):
        """docstring for get_friends_ids"""
        return self.api.friends_ids(*args)

    def get_followers(self, *args):
        """docstring for get_followers_ids"""
        return self.api.followers_ids(*args)

import random
import sys
import time
import twitter
import pymongo
from utils import twitter_helper
from utils import mongo_helper

# Logger
import logging
logger = logging.getLogger(__name__)

# Constant
REST_API_WAIT_SECOND = 5
REST_API_PER_PAGE = 200
# Mongodb
tweets = mongo_helper.get_tweets()
users = mongo_helper.get_users()
events = mongo_helper.get_events()
tweets.ensure_index('id', unique=True, dropDups=True)
users.ensure_index('id', unique=True, dropDups=True)
# Twitter
api = twitter_helper.get_api_fetcher()
stream = twitter_helper.get_stream_fetcher()


def fetch_stream_filter_follow(user_ids_str):
    """Fetch stream of given user (by user_id)"""
    iterator = stream.statuses.filter(follow=user_ids_str)
    _process_tweets_iterator(iterator)


def fetch_stream_filter_keyword(keywords_str):
    """Fetch stream of given keywords"""
    iterator = stream.statuses.filter(track=keywords_str)
    _process_tweets_iterator(iterator)


def fetch_stream_sample():
    """Fetch stream (sample)"""
    iterator = stream.statuses.sample()
    _process_tweets_iterator(iterator)


def fetch_statuses_home_timeline_all(api_user, user_id):
    """Fetch home timeline of given user"""
    iterator_method = api_user.statuses.home_timeline
    # FIXME fetch only unfetched pages
    # FIXME store relationship between user and tweets
    count = _walk_pages(
        iterator_method,
        iter_func=lambda t: _set_tweet_home_timeline(t, user_id),
        iter_params={'count': REST_API_PER_PAGE,
            'include_rts': 1,
            'trim_user': 0})
    return count


def _set_tweet_home_timeline(tweet, user_id):
    if 'r' not in tweet:
        tweet['r'] = {}
    if 'home_timeline' not in tweet['r']:
        tweet['r']['home_timeline'] = []
    tweet['r']['home_timeline'].append(user_id)


def fetch_statuses_user_timeline_all(user_id):
    """Fetch all public tweets of given user (by user_id)"""
    iterator_method = api.statuses.user_timeline
    count = 0

    # fetch user
    user = get_user_by_id_str(user_id)
    logger.debug("User ID: %s" % user['id'])

    # before oldest tweet in db
    oldest_tweet = mongo_helper.get_oldest_tweet(
        {'user.id': user['id']})
    if oldest_tweet:
        max_id = oldest_tweet['id']
        logger.debug("Pick max_id as %d" % max_id)
        count += _walk_pages(
            iterator_method,
            iter_func=lambda t: _set_tweet_home_timeline(t, user_id),
            iter_params={
            'user_id': user_id, 'count': REST_API_PER_PAGE,
            'include_rts': 1, 'trim_user': 0,
            'max_id': (max_id - 1)})

    # after latest tweet in db
    since_id = 1
    latest_tweet = mongo_helper.get_latest_tweet(
        {'user.id': user['id']})
    if latest_tweet:
        since_id = latest_tweet['id']
        logger.debug("Pick since_id as %d" % since_id)

    count += _walk_pages(
        iterator_method,
        iter_func=lambda t: _set_tweet_home_timeline(t, user_id),
        iter_params={
        'user_id': user_id, 'count': REST_API_PER_PAGE,
        'include_rts': 1, 'trim_user': 0,
        'since_id': since_id})
    return count


def get_user_by_screen_name(screen_name):
    """Fetch user profile with screen name

    If a user with given screen name does not exists in database,
    use REST API.
    """
    matched = users.find_one({'screen_name': screen_name})
    if not matched:
        return fetch_user(screen_name=screen_name)
    return matched


def get_user_by_id_str(id_str):
    """Fetch user doc with user id

    If a user with given user id does not exists in database,
    use REST API.
    """
    if isinstance(id_str, int):
        id_str = str(id_str)
    matched = users.find_one({'id_str': id_str})
    if not matched:
        return fetch_user(user_id=id_str)
    return matched


def fetch_user(**kwargs):
    """Fetch user with given params"""
    user = api.users.show(**kwargs)
    try:
        users.save(user)
    except pymongo.errors.DuplicateKeyError:
        logger.debug("Actual name is %s" % user['name'])
    return user


def fetch_users(user_ids):
    """Fetch users with given id list"""
    MAX_LOOKUP = 100
    not_found = user_ids[:]
    result = []
    for user in users.find({'id': {'$in': user_ids}}):
        not_found.remove(user['id'])
        result.append(user)
    while len(not_found):
        to_do = not_found[0:MAX_LOOKUP]
        not_found = not_found[MAX_LOOKUP:]
        ids = ','.join([str(i) for i in to_do])
        for user in api.users.lookup(user_id=ids):
            users.save(user)
            result.append(user)
    return result


def _walk_pages(iterator_method, iter_params={}, iter_func=None):
    """Fetch pages with given REST API params"""
    count = 0
    params = iter_params.copy()
    params['page'] = 1
    while True:
        try:
            iterator = iterator_method(**params)
            count += _process_tweets_iterator(iterator, iter_func)
            if not iterator:
                logger.debug("Done")
                break

            count += len(iterator)
            logger.debug("Page %d Total %d" % (params['page'], count))
            params['page'] += 1
        except twitter.TwitterError as exception:
            logger.error("Error: %s so sleep and try again" % str(exception))
            time.sleep(REST_API_WAIT_SECOND)
    return count


def _process_tweets_iterator(iterator, iter_func=None):
    """Process given iterator: save tweets and users"""
    count = 0
    for tweet in iterator:
        # ignore non-tweet
        if 'id_str' not in tweet:
            continue
        # apply iter_func
        if iter_func:
            iter_func(tweet)
        # process user
        user = users.find_one({'id': tweet['user']['id']})
        if not user:
            if 'screen_name' in tweet['user']:  # include user info
                user = tweet['user'].copy()
                users.save(user)
            else:  # does not include user info
                user = get_user_by_id_str(tweet['user']['id_str'])
        tweet['user'] = {'id': user['id'], 'id_str': user['id_str']}
        # save tweet
        try:
            tweets.save(tweet)
            count += 1
        except pymongo.errors.DuplicateKeyError:
            pass
    return count


def fetch_network(user_id):
    user = get_user_by_id_str(user_id)
    if 'r' in user and 'graph' in user['r']:
        return
    if 'r' not in user:
        user['r'] = {}
    friends = _walk_ids_cursor(api.friends.ids, user_id=user['id'])
    followers = _walk_ids_cursor(api.followers.ids, user_id=user['id'])
    mutuals = list(set(followers) & set(friends))
    neighbors = list(set(followers) | set(friends))
    user['r']['graph'] = {'friends': friends, 'followers': followers,
        'mutuals': mutuals, 'neighbors': neighbors}
    users.save(user)
    # fetch sample of neighbors
    MAX_SAMPLE = 50
    if len(neighbors) > MAX_SAMPLE:
        sample_ids = random.sample(neighbors, MAX_SAMPLE)
    else:
        sample_ids = neighbors[:]
    fetch_users(sample_ids)
    return user


def _walk_ids_cursor(method, **kwargs):
    result = []
    params = kwargs.copy()
    params['cursor'] = -1
    while True:
        r = method(**params)
        result += r['ids']
        params['cursor'] = r['next_cursor']
        if not params['cursor']:
            break
    return result

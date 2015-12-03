import md5
import hmac
import urllib
import hashlib
import requests
import lxml.etree
from base64 import b64encode
from urlparse import urlparse
from datetime import datetime

from amazonmws.const import (API_ENDPOINT_DOMAIN, VALID_FEED_TYPES,
                             VALID_FEED_PROCESSING_STATUS)


@aliased
class Client(object):
    def __init__(self, user_agent=None,
                 endpoint_locale=API_ENDPOINT_LOCALE_US):
        self.set_user_agent(user_agent)

        self.endpoint = 'https://%s%s' % (ENDPOINT_DOMAIN, endpoint_locale)
        self.endpoint_locale = endpoint_locale

    def _request(self, operation, parameters, method='GET'):
        pass

    def _calculate_signature(self, parameters, method='GET'):
        netloc = urlparse(self.endpoint).netloc.lower()
        signature = hmac.new(str(self.access_passwd).encode(),
                             b'%s\n%s\n%s\n%s' % (method, netloc, '/',
                                                  str(parameters)),
                             hashlib.sha256).digest()
        return b64encode(signature)

    def set_user_agent(self, user_agent=None):
        try:
            # User-Agent cannot be None, if None generate one.
            if user_agent is None or len(str(user_agent).strip()) < 1:
                raise UserAgentHeaderMissing()
            user_agent = str(user_agent).strip()
            # User-Agent must be in the following format: app/version (lang).
            if USER_AGENT_FORMAT.match(user_agent) is None:
                raise UserAgentHeaderMalformed(user_agent)
            # User-Agent must have a Language= attribute.
            if USER_AGENT_LANGUAGE_FORMAT.search(user_agent) is None:
                raise UserAgentHeaderLanguageAttributeMissing(user_agent)
            # User-Agent must not exceed 500 characters.
            if len(user_agent) > 500:
                raise UserAgentHeaderMaximumLengthExceeded(user_agent)
        except UserAgentHeaderMissing:
            user_agent = 'amazon-mws/1.0.0 (Language=Python)'
        finally:
            if len(user_agent) > 500:
                raise UserAgentHeaderMaximumLengthExceeded(user_agent)
            self.user_agent = user_agent

    @Alias('SubmitFeed')
    def submit_feed(self, feed_content, feed_type, marketplace_list=None,
                    purge_replace=False):
        if len(feed_content) > 2147483647:
            # TODO: Raise SubmitFeedContentTooLarge exception.
            pass
        if feed_type not in VALID_FEED_TYPES:
            # TODO: Raise InvalidFeedType exception.
            pass
        parameters = Parameters()
        parameters['FeedContent'] = feed_content
        parameters['FeedType'] = feed_type
        parameters['PurgeAndReplace'] = purge_replace
        return self._request('SubmitFeed', parameters)

    @Alias('GetFeedSubmissionList')
    def get_feed_submission_list(self, feed_submission_id_list=None,
                                 max_count=10, feed_type_list=None,
                                 feed_processing_status_list=None,
                                 submitted_from_date=None,
                                 submitted_to_date=None):
        if max_count < 1 or max_count > 100:
            # TODO: Raise InvalidMaxCount
            pass
        if (feed_processing_status_list not None and
            feed_processing_status_list not in VALID_FEED_PROCESSING_STATUS):
            # TODO: Raise InvalidFeedProcessingStatus exception.
            pass
        if (submitted_from_date not None and
            not validate_iso8601_date(submitted_from_date)):
            # TODO: Raise InvalidISO8601Date exception.
            pass
        if (submitted_to_date not None and
            not validate_iso8601_date(submitted_to_date)):
            # TODO: Raise InvalidISO8601Date exception.
            pass
        parameters = Parameters()
        if feed_submission_id_list not None:
            parameters['FeedSubmissionIdList'] = feed_submission_id_list
        parameters['MaxCount'] = max_count
        if feed_type_list not None:
            parameters['FeedTypeList'] = feed_type_list
        if feed_processing_status_list not None:
            parameters['FeedProcessingStatusList'] =\
            feed_processing_status_list
        if submitted_from_date not None:
            parameters['SubmittedFromDate'] = submitted_from_date
        if submitted_to_date not None:
            parameters['SubmittedToDate'] = submitted_to_date
        return self._request('GetFeedSubmissionList', parameters)

    @Alias('GetFeedSubmissionListByNextToken')
    def get_feed_submission_list_by_next_token(self, next_token):
        parameters = Parameters()
        parameters['NextToken'] = next_token
        return self._request('GetFeedSubmissionListByNextToken', parameters)

    @Alias('GetFeedSubmissionCount')
    def get_feed_submission_count(self, feed_type_list=None,
                                  feed_processing_status_list=None,
                                  submitted_from_date=None,
                                  submitted_to_date=None):
        if (feed_processing_status_list not None and
            feed_processing_status_list not in VALID_FEED_PROCESSING_STATUS):
            # TODO: Raise InvalidFeedProcessingStatus exception.
            pass
        if (submitted_from_date not None and
            not validate_iso8601_date(submitted_from_date)):
            # TODO: Raise InvalidISO8601Date exception.
            pass
        if (submitted_to_date not None and
            not validate_iso8601_date(submitted_to_date)):
            # TODO: Raise InvalidISO8601Date exception.
            pass
        parameters = Parameters()
        if feed_type_list not None:
            parameters['FeedTypeList'] = feed_type_list
        if feed_processing_status_list not None:
            parameters['FeedProcessingStatusList'] =\
            feed_processing_status_list
        if submitted_from_date not None:
            parameters['SubmittedFromDate'] = submitted_from_date
        if submitted_to_date not None:
            parameters['SubmittedToDate'] = submitted_to_date
        return self._request('GetFeedSubmissionCount', parameters)

    @Alias('CancelFeedSubmissions')
    def cancel_feed_submissions(self, feed_type_list=None,
                                feed_processing_status_list=None,
                                submitted_from_date=None,
                                submitted_to_date=None):
        if (feed_processing_status_list not None and
            feed_processing_status_list not in VALID_FEED_PROCESSING_STATUS):
            # TODO: Raise InvalidFeedProcessingStatus exception.
            pass
        if (submitted_from_date not None and
            not validate_iso8601_date(submitted_from_date)):
            # TODO: Raise InvalidISO8601Date exception.
            pass
        if (submitted_to_date not None and
            not validate_iso8601_date(submitted_to_date)):
            # TODO: Raise InvalidISO8601Date exception.
            pass
        parameters = Parameters()
        if feed_type_list not None:
            parameters['FeedTypeList'] = feed_type_list
        if feed_processing_status_list not None:
            parameters['FeedProcessingStatusList'] =\
            feed_processing_status_list
        if submitted_from_date not None:
            parameters['SubmittedFromDate'] = submitted_from_date
        if submitted_to_date not None:
            parameters['SubmittedToDate'] = submitted_to_date
        return self._request('CancelFeedSubmissions', parameters)

    @Alias('GetFeedSubmissionResult')
    def get_feed_submission_result(self, feed_submission_id):
        parameters = Parameters()
        return self._request('GetFeedSubmissionResult', parameters)


class Parameters(dict):
    def __init__(self, self):
        dict.__init__(self)

    def __setitem__(self, key, value):
        if type(value) is int or type(value) is bool:
            value = str(value).lower()
        dict.__setitem__(key, value)

    def __str__(self):
        return ''.join(['&%s=%s' % (key, urllib.quote(parameters[key]).\
                                    replace('%7E', '~')) for key in\
                                    sorted(self.keys())])[1:]


class Alias(object):
    def __init__(self, *aliases):
        self.aliases = set(aliases)

    def __call__(self, f):
        f._aliases = self.aliases
        return f


def aliased(aliased_class):
    original_methods = aliased_class.__dict__.copy()
    for name, method in original_methods.iteritems():
        if hasattr(method, '_aliases'):
            for alias in method._aliases - set(original_methods):
                setattr(aliased_class, alias, method)
    return aliased_class


def validate_iso8601_date():
    pass


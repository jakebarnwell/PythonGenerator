import re
import random
import hashlib

from django.core.cache import cache
from django.utils.http import http_date
from django.http import Http404
from django.conf import settings

from rvcms.cms.views import staticpage

EMAIL_LINK_RE = re.compile(r'<a\s.*href=["|\']mailto:[^>]+>.*?</a>')  # find email address links
EMAIL_TEXT_RE = re.compile(r'\b[-.\w]+@[-.\w]+\.[a-z]{2,4}\b')        # find email address text only
EMAIL_IGNORE_RE = re.compile(r'''
(
   <script\s?[^>]*>.*?</script>|           # ignore email addresses in script blocks
   <style\s?[^>]*>.*?</style>|             # ignore in style blocks
   <head\s?[^>]*>.*?</head>|               # ignore in the head section
   (?:value|content)=["|\'][^"|\']*["|\']  # ignore tags with value= or content=
)
''', re.DOTALL | re.VERBOSE)


class EmailObfuscatorMiddleware(object):
    """
    Middleware for obfuscating email addresses, by replacing email links
    and email text with javascript code, see the obfuscate_email() function
    for a description.

    If the content is html, runs the content over a regular expression,
    EMAIL_IGNORE_RE, that splits the content in pieces so we can exclude
    ignored areas of the html from being run through the obfuscator.

    On the remaining html, two regular expressions are run, EMAIL_LINK_RE and
    EMAIL_TEXT_RE for replacing email links and email text.
    """

    def obfuscate_email(self, match):
        code_list = []
        for c in match.group(0):
            d = ord(c)
            x = random.randint(0, d)
            if random.randint(0, 1) == 0:
                code_list.append("%d+%d" % (x, d - x))
            else:
                code_list.append("%d-%d" % (d + x, x))
        return '<script type="text/javascript">document.write(String.fromCharCode(%s))</script>' % ",".join(code_list)

    def process_response(self, request, response):
        # only run filter when not in admin
        if not request.META["PATH_INFO"].startswith("/admin/"):
            # only run on html pages (check required when using Django to serve static media)
            if "text/html" in response["Content-Type"] or "application/xhtml+xml" in response["Content-Type"]:
                # run our email address ignore regex to exclude parts from being processed
                parts = EMAIL_IGNORE_RE.split(response.content)

                # if there is only one part, we can check the whole document
                if len(parts) == 1:
                    response.content = EMAIL_LINK_RE.sub(self.obfuscate_email, response.content)  # obfuscate links
                    response.content = EMAIL_TEXT_RE.sub(self.obfuscate_email, response.content)  # obfuscate text
                else:
                    # otherwise we only obfuscate emails in odd parts
                    count = 1
                    response.content = ""

                    # loop through the parts (split by our email ignore regex)
                    for part in parts:
                        if not part is None:
                            # odd parts are to be checked for email addressed, even parts ignored
                            if count % 2:
                                part = EMAIL_LINK_RE.sub(self.obfuscate_email, part)  # obfuscate links
                                part = EMAIL_TEXT_RE.sub(self.obfuscate_email, part)  # obfuscate text
                            # add the pieces back together, even parts remain untouched
                            response.content += part
                        count += 1
        return response


class StaticPageFallbackMiddleware(object):
    """
    Middleware that display static pages.  This middleware should be
    second to last in your MIDDLEWARE_CLASSES list in settings.py, it must be
    before RedirectFallbackMiddleware.
    """


    def process_response(self, request, response):
        if response.status_code != 404:
            # No need to check for a staticpage for non-404 responses.
            return response
        #noinspection PyBroadException
        try:
            return staticpage(request, request.path_info)
            # Return the original response if any errors happened. Because this
            # is a middleware, we can't assume the errors will be caught.
        except Http404:
            return response
        except:
            if settings.DEBUG:
                raise
            return response


class CachedGetMiddleware(object):
    """
    Handles conditional GET operations. If the response has an ETag or
    Last-Modified header, and the request has If-None-Match or
    If-Modified-Since, the response is replaced by an HttpNotModified.

    Also sets the Date and Content-Length response-headers to help caching.

    This is modification of the django.middleware.http.ConditionalGetMiddleware
    middleware.
    """

    def process_response(self, request, response):
        # only cache when response code is 200, not 404, etc.
        if response.status_code == 200:
            url = "http://" + request.META["HTTP_HOST"] + request.path
            if request.META["QUERY_STRING"]:
                url += "?" + request.META["QUERY_STRING"]
            cache_key = "page_cache_%s" % hashlib.md5(settings.SECRET_KEY + url).hexdigest()

            prev_date = cache.get(cache_key)
            if not prev_date:
                prev_date = http_date()
                cache.set(cache_key, prev_date)
                response["Last-Modified"] = prev_date
            response["Date"] = http_date()

            if not response.has_header("Content-Length"):
                response["Content-Length"] = str(len(response.content))

            response["ETag"] = hashlib.md5(response.content).hexdigest()
            if response.has_header("ETag"):

                if_none_match = request.META.get("HTTP_IF_NONE_MATCH", None)
                # Limit to 32 character because Apache can add -gzip at the end on some servers.
                if if_none_match:
                    if_none_match = if_none_match[:32]

                if if_none_match == response["ETag"]:
                    # Setting the status is enough here. The response handling path
                    # automatically removes content for this status code (in
                    # http.conditional_content_removal()).
                    response.status_code = 304

            if response.has_header("Last-Modified"):
                if_modified_since = request.META.get("HTTP_IF_MODIFIED_SINCE", None)
                if if_modified_since == response["Last-Modified"]:
                    # Setting the status code is enough here (same reasons as above)
                    response.status_code = 304

        return response

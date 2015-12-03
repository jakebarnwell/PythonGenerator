import os
import email
import time
import logging
import re
import hashlib
from datetime import datetime
from tornado.web import RequestHandler, asynchronous, HTTPError
from tornado.ioloop import IOLoop
from models import Content

logger = logging.getLogger(__file__)

READ_SIZE = 64*1024     # 64k
RANGE_REG = re.compile(r'bytes ([0-9]+)-([0-9]+)\/([0-9]+)')     # doesn't accept '*', need to know

class StreamingContentHandler(RequestHandler):
    def prepare(self):
        self.file_ = None
        self.content_obj = None

    def on_connection_close(self):
        self.on_finish()

    def on_finish(self):
        '''Clean up the open file!!'''
        if self.file_ != None:
            self.file_.close()
            self.file_ = None
        self.content_obj = None

    def head(self, id_):
        return self.get(id_, False)

    def parse_crange_hdr(self, request):
        # TODO: move over to utilities :)
        # parse and verify the content-range header
        try:
            range_hdr = request.headers['content-range']
        except KeyError:
            raise HTTPError(400, 'Request must have a content-range header')

        # make sure the format is correct
        range_match = RANGE_REG.match(range_hdr)
        if range_match == None:
            raise HTTPError(400, 'Content-Range {} invalid syntax'.format(range_hdr))

        # check values
        # NOTE: regex already ensures positive numbers
        range_start, range_end, content_size = [int(x) for x in range_match.groups()]
        if range_start > range_end:
            raise HTTPError(400, 'Content-Range {} invalid, s > e'.format(range_hdr))

        # make sure range is within size
        if range_start >= content_size or range_end >= content_size:
            raise HTTPError(400, 'Content-Range {} invalid, range not within size'.format(range_hdr))

        # make sure request length == range size
        range_length = range_end-range_start+1
        if range_length != len(request.body):
            raise HTTPError(400, 'Specified range length, {}, != request body length, {}. Content-Range {}'.format(range_length, len(request.body), range_hdr))

        return range_start, range_end, content_size

    @asynchronous
    def post(self, id_):
        # TODO: This is very insecure as a single request can request a file of
        #       X billion GBs and cause your computer to try and create it.
        #       Best solution is to patch tornado's inbound content handling to
        #       allow streaming of request bodies for handlers that request it.
        #       It also allows a requester to trigger a re-hash of the entire
        #       file with a single byte body.

        rstart, rend, content_size = self.parse_crange_hdr(self.request)
#        print('Got Content range {}-{}/{}'.format(rstart, rend, content_size))

        # get the content object
        try:
            self.content_obj = Content.objects.get(pk=id_)
        except Content.DoesNotExist:
            raise HTTPError(404)

        # open the file for writing
        try:
            # dumb bug with Django file objects and getting the correct mode, so do it myself
            self.file_ = open(self.content_obj.the_file.path, 'r+b')
        except IOError:
            raise HTTPError(500, 'The content object pk={} has no file'.format(self.content_obj.pk))

        # write out this chunks data
        self.file_.seek(rstart)
        try:
            self.file_.write(self.request.body)
        except IOError as e:
            raise HTTPError('IOError writing file: {}'.format(e))

#        print('Wrote out {} bytes'.format(len(self.request.body)))

        # MAYBE: write out the data in 64k blocks
            # use IOLoop add_callback to write small blob then reliquish control

        # if we've just done the last chunk
        if rend + 1 == content_size:
            self._hash_block()
        else:
            self.write({})
            self.finish()

    def _hash_block(self):
        # TEMP: just to make stack trace readable...
        self.request.body = ''

        # TODO: Want to delegate to "boring task" process, rather than inline over here.
        if not hasattr(self, 'hasher'):
#            print('Starting hasher')
            self.hasher = hashlib.sha1()
            self.file_.seek(0)

        data = self.file_.read(READ_SIZE)
        if data:
            self.hasher.update(data)

        if len(data) >= READ_SIZE:
            IOLoop.instance().add_callback(self._hash_block)
        else:
#            print('Finished hashing')
            self.content_obj.original_hash = self.hasher.hexdigest()
            self.content_obj.save()
            self.write({})
            self.finish()

    @asynchronous
    def get(self, id_, include_body=True):
        # get the content object
        try:
            self.content_obj = Content.objects.get(pk=id_)
        except Content.DoesNotExist:
            raise HTTPError(404)

        # get the file and if it's not there, error
        self.file_ = self.content_obj.the_file.file         # got the Django File
        self.file_.open(mode='rb')

        # set up the headers
        self.set_header('Content-Type', self.content_obj.mimetype)
        self.set_header('Accept_Ranges', 'bytes')

        stat_result = os.fstat(self.file_.fileno())

        # handle normal "full" requests
        if 'Range' not in self.request.headers:
            modified = datetime.fromtimestamp(stat_result.st_mtime)
            self.set_header('Last-Modified', modified)

            ims_value = self.request.headers.get('If-Modified-Since')
            if ims_value is not None:
                # TODO: exception handling
                date_tuple = email.utils.parsedate(ims_value)
                if_since = datetime.fromtimestamp(time.mktime(date_tuple))
                if if_since >= modified:
                    self.set_status(304)
                    self.finish()
                    return

            self.bytes_start = 0
            self.bytes_end = stat_result.st_size
        else:
            self.set_status(206)
            # TODO: check the form first, want to 400 anything poop
            range_str = self.request.headers['Range'].split('=', 1)[1]
            start, end = range_str.split('-', 1)

            self.bytes_start = int(start)
            self.file_.seek(self.bytes_start)
            if not end:
                self.bytes_end = stat_result.st_size - 1
            else:
                self.bytes_end = int(end)

            crange_header = 'bytes {}-{}/{}'.format(self.bytes_start, self.bytes_end, stat_result.st_size)
            self.set_header('Content-Range', crange_header)

        self.bytes_remaining = self.bytes_end - self.bytes_start + 1
        self.set_header('Content-Length', str(self.bytes_remaining))
        self.flush()

        if not include_body:
            self.finish()
            return

        # start streaming
        self.stream_once()

    def stream_once(self):
        if self.request.connection.stream.closed():
            return

        if self.bytes_remaining == 0:
            self.finish()
        else:
            data = self.file_.read(min(self.bytes_remaining, READ_SIZE))
            self.bytes_remaining -= len(data)
            self.request.connection.stream.write(data, self.stream_once)


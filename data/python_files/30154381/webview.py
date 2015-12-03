import sys, re, time
import urllib2, urllib, urlparse
try:
    from collections import defaultdict
except:
    class defaultdict(dict):
        def __init__(self, default_factory=None, *a, **kw):
            if (default_factory is not None and
                not hasattr(default_factory, '__call__')):
                raise TypeError('first argument must be callable')
            dict.__init__(self, *a, **kw)
            self.default_factory = default_factory
        def __getitem__(self, key):
            try:
                return dict.__getitem__(self, key)
            except KeyError:
                return self.__missing__(key)
        def __missing__(self, key):
            if self.default_factory is None:
                raise KeyError(key)
            self[key] = value = self.default_factory()
            return value
        def __reduce__(self):
            if self.default_factory is None:
                args = tuple()
            else:
                args = self.default_factory,
            return type(self), args, None, None, self.items()
        def copy(self):
            return self.__copy__()
        def __copy__(self):
            return type(self)(self.default_factory, self)
        def __deepcopy__(self, memo):
            import copy
            return type(self)(self.default_factory,
                              copy.deepcopy(self.items()))
        def __repr__(self):
            return 'defaultdict(%s, %s)' % (self.default_factory,
                                            dict.__repr__(self))

__version__ = "1.0"
__author__ = "Derek Hildreth"
__author_email__ = "derek@derekhildreth.com"

DESCRIPTION = '''%prog allows you to programmically connect with and
control a Canon Network Web Cam using their WebView HTTP Specs (wvhttp).
%prog is able to connect with at least the following: Canon VB-C60,
VB-C500D/VD, VB-C300, VB-C50i/R, or VB-C50Fi/FSi.  See README for more
information.'''

USAGE = "%prog [options] hostname"
VERSION = "%prog v" + __version__

def make_url_params(params):
    '''Create a URL for use with webview command specifications. Will ignore
       blank values.'''

    full_url_params = urllib.urlencode(params)
    try:
        url_params = urlparse.parse_qs(full_url_params)
    except AttributeError:
        import cgi
        url_params = cgi.parse_qs(full_url_params)

    # Convert from dictionary of lists to dictionary of strings
    for key, value in url_params.items():
        url_params[key] = value[0]

    return urllib.urlencode(url_params)

def timestamp():
    '''Return the current timestamp.'''

    return time.strftime("%Y%m%dT%H%M%S", time.gmtime())

def write_to_file(filename, return_data, mime_type=''):
    '''Write the data of the recently grabbed url to disk, while trying to
       be smart about file extensions if we need to be.'''

    fn = filename
    type = "w"

    try:
        if return_data:
            if ("jpeg" in mime_type) or (("jpg" or "jpeg") in fn):
                fn = filename + '.jpg'
                ft = "wb"
            elif ("text/plain" in mime_type) or ("txt" in fn):
                fn = filename + '.txt'
            #elif "multipart/x-mixed-replace" in mime_type:
            #    fn = filename
            #    ft = "wb"

            out = open(fn, ft)
            out.write(return_data)
            out.close()
            return True
    except:
        return False

class CustomException(Exception):
    '''Handles custom exception messages for WebView classes.'''

    def __init__(self, _msg):
        self.msg = _msg
    def __str__(self):
        return repr(self.msg)


class ConnectionError(CustomException):
    '''Raised when there is a general problem with the connection.'''

    pass


class OpenError(CustomException):
    '''Raised when there is a problem opening the session.'''

    pass


class WebViewTop(object):
    '''Defines a set of commands that are used in WebView classes
       which inherit this class.'''

    def __init__(self, host, username='', password=''):
        '''Initial setup for when the class object is instantiated.  The
           hostname is required. If a username or password is supplied, then
           the WebView object will automatically create an opener that knows
           how to login.'''

        if host.startswith("http://"):
            self.base_url = host
        else:
            self.base_url = "http://" + host

        self.connection_id = ''

        if (username or password):
            self.un = username
            self.pw = password
            self.create_opener()

    def create_opener(self):
        '''Create an url opener that will know how to login.'''

        passman = urllib2.HTTPPasswordMgrWithDefaultRealm()
        passman.add_password("User", self.base_url, self.un, self.pw)
        passman.add_password("Administrator", self.base_url, self.un, self.pw)
        authhandler = urllib2.HTTPBasicAuthHandler(passman)

        opener = urllib2.build_opener(authhandler)
        urllib2.install_opener(opener)

    def grab_url(self, url, return_type=False):
        '''Grab the raw page contents and mime-type of the given url.'''

        request = urllib2.urlopen(url)
        if return_type:
            return request.read(), request.info()
        else:
            return request.read()


class WebView(WebViewTop):
    '''Contains methods for connecting, managing sessions, and controlling
       a Canon network camera using the WV-HTTP New Commands Specifications.
       (firmware update may be required to use these methods;  Otherwise use
       the older "compatible commands" in the WebViewCompat object).

       Compatible with:
       VB-C60, ...

       Usage Example:
           from include.webview import WebView
           webobject = WebView(host='web.com', username='foo', password='bar')
           webobject.open(video='jpg:640x480:3:30000')
           image = webobject.image()
           output = open("webview_image.jpg", "w")
           output.write(image)
           output.close()
           webobject.close()

       For more information, refer to the HTTP WebView Protocol Spec
       http://scribd.com/doc/39808868/YT1-1019-001-HTTPWebViewProtocolSpecs'''

    ############################################################################
    # Session Control Commands
    ############################################################################
    def open(self, video='', priority=''):
        '''This function creates a WV-HTTP session. When creating a
           privileged session, specify the priority with "priority". This
           priority level is used for access management, control privileges
           management, and so on. Session life spans differ depending on
           the priority, with privileged sessions (those with a priority of 5
           or higher) unlimited, and general sessions (those with a priority
           of 0) limited to the maximum connection time (the set value).

           Maximum connections limit exceeded: 503 error

           Raw HTML Returns:
               s:=<session identifier>
               s.origin:=<camera address>:<HTTP port>
               s.duration==<time remaining in the session>
               s.priority:=<session priority level>
               v:=<video stream>

               s:=eaea-8e04c059
               s.origin:=192.168.0.2:1024
               s.duration==3600
               s.priority:=0
               v:=jpg:640x480:3:30000
           '''

        params = {'v' : video,
                  'priority' : priority}
        url_params = make_url_params(params)
        url = self.base_url + "/-wvhttp-01-/open.cgi?%s" \
              "" % (url_params)
        return_data = self.grab_url(url)
        if "Invalid Parameter Value" in return_data:
            raise OpenError("Invalid parameter specified in open.cgi")

        regex_i = re.compile("s:=(.*)")
        matchobj_i = re.search(regex_i, return_data)
        if not (matchobj_i):
            raise OpenError("unable to obtain session id from open.cgi")
        else:
            self.connection_id = matchobj_i.groups()[0]

        return return_data

    def close(self):
        '''This function deletes the WV-HTTP session.

           Raw HTML Returns:
           OK.
        '''

        url = self.base_url + '/-wvhttp-01-/close.cgi?s=%s' % self.connection_id
        return self.grab_url(url)

    def claim_control(self):
        '''This function requests camera control privileges. The control
           privilege allocation time is determined by the session's priority
           level, with privileged sessions unlimited, andothers set to a
           finite value (the set value).

           Raw HTML Returns:
           s.control:=(...)
              (If the state of control privileges has changed)
                 enabled:<allocated time>  (control right secured)
                 waiting:<waiting time>    (waiting to secure control right)
              (If the state of control privileges has not changed)
                 enabled:<allocated time>  (control right secured)
                 waiting:<waiting time>    (waiting to secure control right)
                 disabled  (failed to secure control privilege)
        '''

        url = self.base_url + '/-wvhttp-01-/claim.cgi?s=%s' % self.connection_id
        return self.grab_url(url)

    def yield_control(self):
        '''This function releases camera control privileges, or cancels the
           state of waiting for camera control privileges.

           Raw HTML Returns:
           s.control:=(...)
              (If the state of control privileges has changed)
                 disabled   (will also be notified as an event from info.cgi)
              (If the state of control privileges has not changed)
                 disabled
        '''

        url = self.base_url + '/-wvhttp-01-/yield.cgi?s=%s' % self.connection_id
        return self.grab_url(url)

    def session(self, video='', priority=''):
        '''This function retrieves or changes session-specific
           attributes. The currently supportedsession-specific attributes
           are priority level and video stream.  The details of a changed
           item will be notified as an event in info.

           Raw HTML Returns:
           s.priority:=<new priority level>
           v:=<new video stream>
        '''

        params = {'v' : video,
                  'priority' : priority}
        url_params = make_url_params(params)

        url = self.base_url + "/-wvhttp-01-/session.cgi?%s" \
              "" % (url_params)

        return self.grab_url(url)

    ############################################################################
    # Video Retrieval Commands
    ############################################################################
    def image(self, use_session_id=True, video='', pan='', tilt='', zoom=''):
        '''This function requests a JPEG still image. Operations differ
        as follows, depending onwhether or not a session identifier
        is specified:

        * When the session identifier is specified: The session's
          video stream setting is used.

        * If, however, the type of the video stream set is mp4, then
          a usable jpg stream will be selected, and the session's video
          stream setting will be changed. This command is prohibited during
          the transmission of a video stream using video.cgi (this will
          result in a 408 error). Camera control parameters are ignored.

        * When the session identifier is not specified: Selection
          will be made based on the video stream specifier v. Camera
          control parameters can be used to specify the shooting position
          (note: this will be ignored if the control privilege cannot
          be secured).

        Although it is up to the application to decide how
        to differentiate when using these, the method for specifying the
        session identifier is suited for use in displaying a pseudo
        video by repeatedly sending JPEG still images. To retrieve a
        single JPEG still image alone, you can use image.cgi without
        specifying a session identifier.

        Will return 408 error if video is used at the same time.'''

        params = {}
        if use_session_id:
            params['s'] = self.connection_id

        params['v'] = video
        params['pan'] = pan
        params['tilt'] = tilt
        params['zoom'] = zoom

        url_params = make_url_params(params)

        url = self.base_url + "/-wvhttp-01-/image.cgi?%s" \
              "" % (url_params)

        return self.grab_url(url)

    def video(self, use_session_id=True, video='', duration='', v_type=''):
        '''This function requests transmission of the video
        stream. Operations differ as follows, depending on whether or
        not a session identifier is specified:

        * When the session identifier is specified: The session's video stream
          setting is used. This command is prohibited during the transmission of
          a video stream or a JPEG still image (image.cgi) (this will result
          in a 408 error). The transmission process will continue until either
          the session ends or the client cuts the connection.

        * When the session identifier is not specified: Selection will be made
          based on the video stream specifier v. The transmission process will
          continue until either the period specified by duration comes to an
          end, or the client cuts the connection.

        The video stream can use type to specify the transmission control
        method (buffering policy). The transmission control method and the
        session identifier specification are unrelated to each other.'''

        raise SystemExit("This function not ready")

        params = {}
        if use_session_id:
            params['s'] = self.connection_id

        params['v'] = video
        params['duration'] = duration
        params['type'] = v_type

        url_params = make_url_params(params)

        url = self.base_url + "/-wvhttp-01-/video.cgi?%s" \
              "" % (url_params)

        return self.grab_url(url)

    ############################################################################
    # Information Retrieval Commands
    ############################################################################
    def info(self, use_session_id=True, item='', v_type='', timeout=''):
        '''This function retrieves various types of
        information. Operations differ as follows, depending on whether
        or not a session identifier is specified.'''

        params = {}
        if use_session_id:
            params['s'] = self.connection_id

        params['item'] = item
        params['type'] = v_type
        params['timeout'] = timeout

        url_params = make_url_params(params)

        url = self.base_url + "/-wvhttp-01-/info.cgi?%s" \
              "" % (url_params)

        return self.grab_url(url)

    def panorama(self, use_session_id=True, panorama=''):
        '''This function retrieves panorama image data. If there is no
        session specification, then this is limited to administrators.'''

        params = {}
        if use_session_id:
            params['s'] = self.connection_id

        params['panorama'] = panorama

        url_params = make_url_params(params)

        url = self.base_url + "/-wvhttp-01-/panorama.cgi?%s" \
              "" % (url_params)

        return self.grab_url(url)

    ############################################################################
    # Camera Control Commands
    ############################################################################
    def control(self, use_session_id=True,
                pan='', tilt='', zoom='', priority='', camera_number='',
                exposure='', day_night_mode='', day_night_switching_mode='',
                ae_slow_shutter='', ae_shutter_speed='', ae_brightness='',
                ae_metering='', me_shutter='', me_agc_gain='', white_balance='',
                wb_rb_gain='',  image_stabilization='', noise_reduction='',
                aperature_correction='', shade_correction='',
                shade_correction_param='', focus_mode='', focus_value='',
                zoom_speed='', zoom_operational_speed_pos='',
                zoom_operational_speed_tele='', pan_speed='',
                pan_operational_speed_pan='', pan_operational_speed_lr='',
                specify_tilt_pos_dir='', tilt_operational_speed_pos='',
                tilt_operational_speed_tilt='', view_restriction='',
                external_output_control=''):
        '''This function controls the camera and external output
           terminal. When the external output terminal is to be controlled
           (along with everything but pan, tilt, and zoom speed),camera
           control privileges are necessary (a 301 error occurs if camera
           control privileges cannot be secured). If camera control privileges
           are necessary, operations will differ as follows, depending on
           whether or not a session identifier is specified.'''

        params = {}

        if use_session_id:
            params['s'] = self.connection_id

        params['priority'] = priority
        params['c'] = camera_number
        params['exp'] = exposure
        params['ae.autoss'] = ae_slow_shutter
        params['ae.shutter'] = ae_shutter_speed
        params['ae.brightness'] = ae_brightness
        params['ae.photometry'] = ae_metering
        params['me.shutter'] = me_shutter
        params['me.iris'] = me_agc_gain
        params['wb'] = white_balance
        params['wb.value'] = wb_rb_gain
        params['dn'] = day_night_mode
        params['dn.mode'] = day_night_switching_mode
        params['is'] = image_stabilization
        params['nr'] = noise_reduction
        params['ac'] = aperature_correction
        params['shade'] = shade_correction
        params['shade.param'] = shade_correction_param
        params['focus'] = focus_mode
        params['focus.value'] = focus_value
        params['zoom'] = zoom
        params['zoom.speed'] = zoom_speed
        params['zoom.speed.pos'] = zoom_operational_speed_pos
        params['zoom.speed.dir'] = zoom_operational_speed_tele
        params['pan'] = pan
        params['pan.speed'] = pan_speed
        params['pan.speed.pos'] = pan_operational_speed_pan
        params['pan.speed.dir'] = pan_operational_speed_lr
        params['tilt'] = tilt
        params['tilt.speed'] = specify_tilt_pos_dir
        params['tilt.speed.pos'] = tilt_operational_speed_pos
        params['tilt.speed.dir'] = tilt_operational_speed_tilt
        params['view.restriction'] = view_restriction
        params['o'] = external_output_control

        url_params = make_url_params(params)
        url = self.base_url + "/-wvhttp-01-/control.cgi?%s" \
              "" % (url_params)
        return self.grab_url(url)

    ############################################################################
    # Return Data Functions
    ############################################################################
    def get_camera_open_results(self):
        '''Return dictionary of information on camera open.'''

        results = {}
        connection_id = ""
        origin = ""
        duration = ""
        priority = ""
        video = ""
        return_data = self.open()

        # Setup regex and match object for each return value in message body
        regex_i = re.compile("s:=(.*)")
        regex_o = re.compile("s\.origin:=(.*)")
        regex_d = re.compile("s\.duration==(.*)")
        regex_p = re.compile("s\.priority:=(.*)")
        regex_v = re.compile("v:=(.*)")
        matchobj_i = re.search(regex_i, return_data)
        matchobj_o = re.search(regex_o, return_data)
        matchobj_d = re.search(regex_d, return_data)
        matchobj_p = re.search(regex_p, return_data)
        matchobj_v = re.search(regex_v, return_data)

        if matchobj_i:
            connection_id = matchobj_i.groups()[0]
        if matchobj_o:
            origin = matchobj_o.groups()[0]
        if matchobj_d:
            duration = matchobj_d.groups()[0]
        if matchobj_p:
            priority = matchobj_p.groups()[0]
        if matchobj_v:
            video = matchobj_v.groups()[0]

        results['session identifier'] = connection_id
        results['camera address'] = origin
        results['time remaining'] = duration
        results['session priority'] = priority
        results['video stream'] = video

        return results

    def get_claim_control_results(self):
        '''Return a dictionary type of information reguarding claim control.'''

        control_status = ""
        control_time = ""
        results = {}
        return_data = self.claim_control()

        regex_okay_init        = re.compile("s\.control:=(.*):(.*)")
        regex_okay_changed     = re.compile("s\.control==(.*):(.*)")
        regex_disabled_init    = re.compile("s\.control:=(.*)$")
        regex_disabled_changed = re.compile("s\.control==(.*)$")

        matchobj_oi = re.match(regex_okay_init, return_data)
        matchobj_oc = re.match(regex_okay_changed, return_data)
        matchobj_di = re.match(regex_disabled_init, return_data)
        matchobj_dc = re.match(regex_disabled_changed, return_data)

        if matchobj_oi:
            control_status = matchobj_oi.groups()[0]
            control_time = matchobj_oi.groups()[1]
        elif matchobj_oc:
            control_status = matchobj_oc.groups()[0]
            control_time = matchobj_oc.groups()[1]
        elif matchobj_di:
            control_status = matchobj_di.groups()[0]
        elif matchobj_dc:
            control_status = matchobj_dc.groups()[0]

        results['control time'] = control_time
        results['control status'] = control_status
        return results

    def get_session_results(self):
        '''Return dictionary object of information on session.'''

        results = {}
        priority = ""
        video = ""
        return_data = self.session()

        regex_p = re.compile("s\.priority:=(.*)", re.IGNORECASE)
        regex_v = re.compile("v:=(.*)", re.IGNORECASE)

        matchobj_p = re.search(regex_p, return_data)
        matchobj_v = re.search(regex_v, return_data)

        if matchobj_p:
            priority = matchobj_p.groups()[0]
        if matchobj_v:
            video = matchobj_v.groups()[0]

        results['session priority'] = priority
        results['video stream'] = video
        return results

    def get_yield_control_results(self):
        '''Return dictionary object of information on yield control.'''

        results = {}
        control_status = ""
        return_data = self.yield_control()

        regex_disabled = re.compile("s\.control:=(.*)$")
        matchobj = re.match(regex_disabled, return_data)

        if matchobj:
            control_status = matchobj.groups()[0]

        results['control status'] = control_status
        return results

    def get_readable_presets(self):
        '''Print a human readable list of presets available.'''

        preset = defaultdict(dict)
        legend = {}
        preset_readable = []

        # We don't want to use session id because we want everything in info
        info = self.info(use_session_id=False, item='p')

        #\1: preset number; \2: name,pan,tilt,zoom; \3: value
        regex = re.compile("p\.(\d{1,2})\.(.*):=(.*)")
        matches = regex.findall(info)
        if matches:
            for match in matches:
                preset[match[0]][match[1]] = match[2]

            for (key, value) in sorted(preset.items()):
                legend[key] = value['name.asc']

            for key, value in sorted(legend.items()):
                preset_readable.append((key, value))

        return preset_readable

    def select_preset(self, preset_no):
        '''Select a preset built-into the camera.'''

        # {preset_no: {tilt: 1, pan: 2, zoom, 3}}
        preset = defaultdict(dict)
        preset_dic = { 'cam_no' : "", 'pan' : "", 'tilt' : "", 'zoom' : "",
                       'focus' : "", 'name_asc' : "", 'name_utf8' : "",
                       'ae_brightness' : "" }

        # We don't want to use session id because we want everything in info
        info = self.info(use_session_id=False, item='p')

        #\1: preset number; \2: name,pan,tilt,zoom; \3: value
        regex = re.compile("p\.(\d{1,2})\.(.*):=(.*)")
        matches = regex.findall(info)
        if matches:
            for match in matches:
                preset[match[0]][match[1]] = match[2]

            if preset_no in preset:
                preset_dic = { 'cam_no' : preset[preset_no]['c'],
                    'pan' : preset[preset_no]['pan'],
                    'tilt' : preset[preset_no]['tilt'],
                    'zoom' : preset[preset_no]['zoom'],
                    'focus' : preset[preset_no]['focus'],
                    'name_asc' : preset[preset_no]['name.asc'],
                    'name_utf8' : preset[preset_no]['name.utf8'],
                    'ae_brightness' : preset[preset_no]['ae.brightness']}

        return preset_dic


class WebViewCompat(WebViewTop):
    '''Contains methods for connecting, managing sessions, and controlling
       a Canon network camera using the WV-HTTP Compatible Commands
       Specifications. These are functionally compatible with the WV-HTTP
       of VB-C300 or VB-C50i, and which are a subset of the new commands in
       terms of details.

       Compatible with:
       VB-C50i/VB-C50iR, VB-C300, ...

       Usage Example:
           from include.webview import WebViewCompat
           webobject = WebViewCompat(host='web.com', username='foo', \\
                                     password='bar')
           webobject.OpenCameraServer(video='jpg:640x480:3:30000')
           image = webobject.GetLiveImage()
           output = open("webview_image.jpg", "w")
           output.write(image)
           output.close()
           webobject.CloseCameraServer()

       For more information, refer to the HTTP WebView Protocol Spec
       http://scribd.com/doc/39808868/YT1-1019-001-HTTPWebViewProtocolSpecs'''

    ############################################################################
    # Session Control Commands
    ############################################################################
    def OpenCameraServer(self, priority='', video='', vc_host=''):
        '''This function creates a WV-HTTP session. When creating a
           privileged session,specify the priority with "priority". This
           priority level is used for access management, control privilege
           management, and so on. Session life spans differ depending on
           thepriority, with privileged sessions (those with a priority of 5
           or higher) unlimited, andgeneral sessions (those with a priority
           of 0) limited to the maximum connection time (theset value).'''

        self.video = video
        self.priority = priority
        self.vc_host = vc_host

        params = {'v' : video,
                  'priority' : priority,
                  'vc_host' : vc_host}
        url_params = make_url_params(params)
        url = self.base_url + "/-wvhttp-01-/OpenCameraServer?%s" \
              "" % (url_params)
        return_data = self.grab_url(url)
        if "Invalid Parameter Value" in return_data:
            raise OpenError("Invalid parameter specified in OpenCameraServer")

        regex_i = re.compile("connection_id=(.*)")
        matchobj_i = re.search(regex_i, return_data)
        if not (matchobj_i):
            raise OpenError("unable to obtain session id from OpenCameraServer")
        else:
            self.connection_id = matchobj_i.groups()[0]

        return return_data

    def CloseCameraServer(self):
        '''This function deletes the WV-HTTP session.

           Raw HTML Returns:
           OK.
        '''

        url = self.base_url + '/-wvhttp-01-/CloseCameraServer?connection_id=%s' \
              "" % self.connection_id

        return self.grab_url(url)

    def Priority(self, priority=''):
        '''This function specifies the session's priority level.'''

        params = {'priority' : priority}
        url_params = make_url_params(params)

        url = self.base_url + "/-wvhttp-01-/Priority?connection_id=%s&%s" \
              "" % (self.connection_id, url_params)

        return self.grab_url(url)

    def GetCameraControl(self):
        '''This function requests camera control privileges. The control
           privileges allocation time is determined by the session's
           priority level, with privileged sessions unlimited, andothers
           set to a finite value (the set value).  Refer to GetNotice for
           event information.'''

        url = self.base_url + "/-wvhttp-01-/GetCameraControl?" \
              "%s=%s" % ("connection_id", self.connection_id)

        return self.grab_url(url)

    def ReleaseCameraControl(self):
        '''This function releases camera control privileges, or cancels
           the state of waiting forcamera control privileges. If the control
           privileges have not been secured, then a 301 error will result.'''

        url = self.base_url + "/-wvhttp-01-/ReleaseCameraControl?" \
              "%s=%s" % ("connection_id", self.connection_id)

        return self.grab_url(url)

    ############################################################################
    # Commands Related to Video
    ############################################################################
    def GetOneShot(self, image_size='', frame_rate='', frame_count=''):
        '''This function retrieves a JPEG data stream in multi-part
           format. When multiple framesare specified, the maximum connection
           time is the limit (although privileged users, which are identified
           with the HTTP request's header field Authorization, have no
           time limit).'''

        params = {'image_size' : image_size,
                  'frame_rate' : frame_rate,
                  'frame_count' : frame_count}
        url_params = make_url_params(params)
        url = self.base_url + "/-wvhttp-01-/GetOneShot?%s" \
              "" % (url_params)

        return self.grab_url(url)

    def GetLiveImage(self, timeout=''):
        '''This function retrieves JPEG data. A serial number starting
           with 1 (Livescope-Frame-Number header field) is appended to the
           JPEG data.  Timeout cannot be used with the VB-C60.'''

        params = {'timeout' : timeout}
        url_params = make_url_params(params)

        url = self.base_url + "/-wvhttp-01-/GetLiveImage?connection_id=%s&%s" \
              "" % (self.connection_id, url_params)

        return self.grab_url(url)

    def ChangeImageSize(self, image_size=''):
        '''This function switches to the JPEG stream specified with
           v|image_size. This is effective in cases where JPEG streams with
           multiple sizes can be used.'''

        params = {'image_size' : image_size}
        url_params = make_url_params(params)

        url = self.base_url + "/-wvhttp-01-/ChangeImageSize?connection_id=%s&%s" \
              "" % (self.connection_id, url_params)

        return self.grab_url(url)

    ############################################################################
    # Information Reference Commands
    ############################################################################
    def GetProtocolVersion(self):
        '''This function retrieves the WV-HTTP protocol version.'''

        url = self.base_url + "/-wvhttp-01-/GetProtocolVersion"

        return self.grab_url(url)

    def GetCameraServerInfo(self):
        '''This function retrieves camera server information.'''

        url = self.base_url + "/-wvhttp-01-/GetCameraServerInfo"

        return self.grab_url(url)

    def GetSystemInfo(self, item=''):
        '''This function retrieves system information.'''

        params={'item' : item}
        url_params = make_url_params(params)

        url = self.base_url + "/-wvhttp-01-/GetSystemInfo?%s" \
              "" % url_params
        return self.grab_url(url)

    def GetVideoInfo(self, use_session_id=True, item=''):
        '''Grab the page contents containg webcam system information.'''
        params = {}
        if use_session_id:
            params['s'] = self.connection_id

        params['item'] = item

        url_params = make_url_params(params)

        url = self.base_url + "/-wvhttp-01-/GetVideoInfo?%s" \
              "" % url_params
        return self.grab_url(url)

    def GetCameraInfo(self, camera_id='', item=''):
        '''This function retrieves camera information.'''

        params={'camera_id' : camera_id,
                'item' : item}
        url_params = make_url_params(params)

        url = self.base_url + "/-wvhttp-01-/GetCameraInfo?%s" \
              "" % url_params
        return self.grab_url(url)

    def GetCameraInfoEx(self, camera_id='', item=''):
        '''This function retrieves extended camera information.'''

        params={'camera_id' : camera_id,
                'item' : item}
        url_params = make_url_params(params)

        url = self.base_url + "/-wvhttp-01-/GetCameraInfoEx?%s" \
              "" % url_params
        return self.grab_url(url)

    def GetCameraList(self, language='', character_set=''):
        '''This function retrieves the camera list (the number of cameras
           and camera names).'''

        params={'language' : language,
                'character_set' : character_set}
        url_params = make_url_params(params)

        url = self.base_url + "/-wvhttp-01-/GetCameraList?%s" \
              "" % url_params
        return self.grab_url(url)

    def GetPresetList(self, language='', character_set=''):
        '''This function retrieves the preset list (the number of presets,
           preset names, and the,camera control parameter).'''

        params={'language' : language,
                'character_set' : character_set}
        url_params = make_url_params(params)

        url = self.base_url + "/-wvhttp-01-/GetPresetList?%s" \
              "" % url_params
        return self.grab_url(url)

    def GetPanoramaList(self, item=''):
        '''This function retrieves the panorama image list.'''

        params={'item' : item}
        url_params = make_url_params(params)

        url = self.base_url + "/-wvhttp-01-/GetPanoramaList?%s" \
              "" % url_params
        return self.grab_url(url)

    def GetPanoramaInfo(self, panorama_id='', camera_id='', item=''):
        '''This function retrieves panorama image information.'''

        params={'panorama_id' : panorama_id,
                'camera_id' : camera_id,
                'item' : item}
        url_params = make_url_params(params)

        url = self.base_url + "/-wvhttp-01-/GetPanoramaInfo?%s" \
              "" % url_params
        return self.grab_url(url)

    def GetPanoramaImage(self, use_session_id=True, panorama_id='',
                        camera_id=''):
        '''This function retrieves panorama image data. If there is no
           session specification, thenthis is limited to administrators.'''

        params = {}
        if use_session_id:
            params['s'] = self.connection_id

        params['panorama_id'] = panorama_id
        params['camera_id'] = camera_id

        url_params = make_url_params(params)

        url = self.base_url + "/-wvhttp-01-/GetPanoramaImage?%s" \
              "" % url_params
        return self.grab_url(url)

    ############################################################################
    # Event Retrieval Commands
    ############################################################################
    def GetNotice(self, notice='', timeout=''):
        '''This function waits for an event to occur, and then retrieves
           this event. When an event occurs, the event number is notified with
           the Livescope-Notice header field, and detailed event information
           is notified with the message body. If no event to be notified
           occurs within the prescribed time, then a 404 Operation Timeout
           error will occur. The timeout parameter can be used to specify
           the timeout time.'''

        params={'connection_id' : self.connection_id,
                'notice' : notice,
                'timeout' : timeout}
        url_params = make_url_params(params)

        url = self.base_url + "/-wvhttp-01-/GetNotice?%s" \
              "" % url_params
        return self.grab_url(url)
        #TODO: Add option to return what the notice numbers mean?

    ############################################################################
    # Camera Control Related Commands
    ############################################################################
    def GetPTZSpeedInfo(self, camera_id=''):
        '''This function retrieves the pan, tilt, and zoom movement
           speed and range. The position specification speed is used in the
           position specification of OperateCamera, etc., and the operation
           specification speed is used in the operation specification
           of OperateCameraEx. For VB-C500, it retrieves zoom movement
           speed and range only because VB-C500 does not support pan and
           tilt control.'''

        params={'connection_id' : self.connection_id,
                'camera_id' : camera_id}
        url_params = make_url_params(params)

        url = self.base_url + "/-wvhttp-01-/GetPTZSpeedInfo?%s" \
              "" % url_params
        return self.grab_url(url)

    #TODO: def SetPTZSpeed(self,...):
        '''This function specifies the movement speeds of the selected
           camera's pan, tilt, and zoom. The movement speeds are values
           specific to the session, and do not affect the operations of
           other sessions (or of sessionless commands). For VB-C500, it
           specifies the movement speed of the selected camera's zoom only,
           because VB-C500 does not support pan and tilt control.'''

    def SelectCamera(self, camera_id=''):
        '''This function switches the camera.'''

        params={'connection_id' : self.connection_id,
                'camera_id' : camera_id}
        url_params = make_url_params(params)

        url = self.base_url + "/-wvhttp-01-/SelectCamera?%s" \
              "" % url_params
        return self.grab_url(url)

    def OperateCamera(self, p='', t='', z='', \
                      pan='', tilt='', zoom='',
                      focus_mode='', focus_value='', back_light=''):
        '''This function switches and controls the camera (pan, tilt,
        zoom, focus, and backlight correction). For VB-C500, only camera
        control is available (zoom, backlight compensation) because
        VB-C500 does not support pan, tilt and focus.'''

        params = {'connection_id' : self.connection_id,
                  'p' : p,  # 1 degree units
                  't' : t,
                  'z' : z,
                  'pan' : pan, # 0.01 degree units
                  'tilt' : tilt,
                  'zoom' : zoom,
                  'focus_mode' : focus_mode,
                  'focus_value' : focus_value,
                  'back_light' : back_light}
        url_params = make_url_params(params)
        url = self.base_url + "/-wvhttp-01-/OperateCamera?%s" \
              "" % (url_params)
        return self.grab_url(url)

     #TODO: def OperateCameraEx(self, ...):
        '''This function controls the camera (pan, tilt, zoom, focus,
           shutter speed, white balance, backlight correction, and AE
           lock). One operation can be specified at a time, and multiple
           operations should not be specified (if there is no operation
           specification, then a 406 error will result). For VB-C500, only
           camera control is available (zoom, shutter speed, white balance,
           backlight compensation, AE lock), because VB-C500 does not support
           pan, tilt and focus.'''

    def OperateCameraOnScreen(self, pan='', tilt=''):
        '''This function controls the camera (pan and tilt). For VB-C500,
           it always returns error messages to the OperateCameraOnScreen
           command, because VB-C500 does not support pan and tilt control.'''

        params = {'connection_id' : self.connection_id,
                  'pan' : pan,
                  'tilt' : tilt}
        url_params = make_url_params(params)

        url = self.base_url + "/-wvhttp-01-/OperateCameraOnScreen?%s" \
              "" % (url_params)

        return self.grab_url(url)

     #TODO: def Exposure(self, ...):
        '''This function controls exposure.'''

    def NightMode(self, camera_id='', night_mode=''):
        '''This function retrieves and controls the night mode state. Only
           privileged users(administrator and privileged users) can use
           this command. Also, only cameras thatsupport night mode can
           use this.'''

        params = {'camera_id' : camera_id,
                  'night_mode' : night_mode}
        url_params = make_url_params(params)

        url = self.base_url + "/-wvhttp-01-/NightMode?%s" \
              "" % (url_params)
        return self.grab_url(url)

    #TODO: def CameraControl(self, ...):
        '''This function switches and controls the camera. CameraPosition
           is a high-priority command that can always be used, as long as
           it is not during the shooting of a panorama (note: this command
           is limited to administrators). CameraControl is a low-priority
           command that can only be used when camera control privileges
           are not secured. This command is for sessionless use only.'''

    def ExternalIOCaption(self, language='', character_set=''):
        '''This function retrieves the external input/output name.'''

        params={'language' : language,
                'character_set' : character_set}
        url_params = make_url_params(params)

        url = self.base_url + "/-wvhttp-01-/ExternalIOCaption?%s" \
              "" % url_params
        return self.grab_url(url)

    def ExternalIOConfig(self, use_session_id=True):
        '''This function queries whether or not there is external input/output
           terminal information and a motion detection function.'''

        params = {}
        if use_session_id:
            params['s'] = self.connection_id

        url_params = make_url_params(params)

        url = self.base_url + "/-wvhttp-01-/ExternalIOConfig?%s" \
              "" % url_params
        return self.grab_url(url)

    #TODO: def ExternalIOStatus(self, ...):
        '''This function queries the external input terminal state and
           the results of motion detection.'''

    def ExternalIO(self, output=''):
        '''This function controls the external output terminal. Only
           privileged users (administrators and privileged users) can use
           this command.'''

        params={'o' : output}
        url_params = make_url_params(params)

        url = self.base_url + "/-wvhttp-01-/ExternalIO?%s" \
              "" % url_params
        return self.grab_url(url)

    ############################################################################
    # Return Data Functions
    ############################################################################
    def get_open_camera_server_results(self):
        '''Parses through results from OpenCameraServer'''

        results = {}
        connection_id = ""
        return_data = self.OpenCameraServer()

        regex_i = re.compile("connection_id=(.*)")
        matchobj_i = re.search(regex_i, return_data)

        if matchobj_i:
            connection_id = matchobj_i.groups()[0]

        results['connection identifier'] = connection_id
        return results

    def get_camera_model(self):
        '''Parses through data from GetProtocolVersion'''

        return_data = self.GetProtocolVersion()

        if "02.00" in return_data:
            return "VB-C500/VB-C60"
        elif "01.08" in return_data:
            return "VB-C300"
        elif "01.07" in return_data:
            return "VB-C50i series/VB150"
        elif "01.05" in return_data:
            return "VB100, 101, VB-C10, C10R"
        else:
            return "Unrecognized"

    def get_priority_results(self):
        '''Parses through results from Priority'''

        results = {}
        priority = ""
        return_data = self.Priority()

        regex = re.compile("priority=(.*)")
        matchobj = re.match(regex, return_data)

        if matchobj:
            priority = matchobj_p.groups()[0]

        results['priority'] = priority
        return results

    def select_preset(self, preset_no, print_names=False):
        '''Select a preset built-into the camera.'''

        info = self.GetPresetList()

        # {preset_no: {tilt: 1, pan: 2, zoom, 3}}
        preset = defaultdict(dict)

        preset_dic = {}

        # \1: preset number, \2: name, \3 camera_id, \4 pan, \5 tilt, \6 zoom,
        # \7 back_light, \8 focus_mode
        regex = re.compile("position_(\d{1,2})=(\w.*)\ncamera_id=(\d{1,2})\n" \
                           "pan=?(.\d{1,6}\d{1,6})\ntilt=?(.\d{1,6})\n" \
                           "zoom=?(.\d{1,6})\nback_light=(\w.*)\n" \
                           "focus_mode=(\w.*)", re.MULTILINE)
        customs = [
            ('25', 'Custom: Name1', '1', '', '', '', 'OFF', 'auto'),
            ('26', 'Custom: Name2', '1', '0', '-5', '10', 'OFF', 'auto')
        ]
        matches = regex.findall(info)
        if matches:
            for match in matches:
                preset[match[0]]["name"] = match[1]
                preset[match[0]]["camera_id"] = match[2]
                preset[match[0]]["pan"] = match[3]
                preset[match[0]]["tilt"] = match[4]
                preset[match[0]]["zoom"] = match[5]
                preset[match[0]]["back_light"] = match[6]
                preset[match[0]]["focus_mode"] = match[7]

            if preset_no in preset:
                preset_dic = { 'camera_id' : preset[preset_no]['camera_id'],
                    'pan' : preset[preset_no]['pan'],
                    'tilt' : preset[preset_no]['tilt'],
                    'zoom' : preset[preset_no]['zoom'],
                    'focus_mode' : preset[preset_no]['focus_mode'],
                    'name' : preset[preset_no]['name'],
                    'back_light' : preset[preset_no]['back_light']}

        if customs:
            for match in customs:
                preset[match[0]]["name"] = match[1]
                preset[match[0]]["camera_id"] = match[2]
                preset[match[0]]["pan"] = match[3]
                preset[match[0]]["tilt"] = match[4]
                preset[match[0]]["zoom"] = match[5]
                preset[match[0]]["back_light"] = match[6]
                preset[match[0]]["focus_mode"] = match[7]

            if preset_no in preset:
                preset_dic = { 'camera_id' : preset[preset_no]['camera_id'],
                    'pan' : preset[preset_no]['pan'],
                    'tilt' : preset[preset_no]['tilt'],
                    'zoom' : preset[preset_no]['zoom'],
                    'focus_mode' : preset[preset_no]['focus_mode'],
                    'name' : preset[preset_no]['name'],
                    'back_light' : preset[preset_no]['back_light']}

        legend = {}
        for (key, value) in sorted(preset.items()):
            legend[key] = value['name']

        if print_names:
            print "Preset numbers and names:"
            for key, value in sorted(legend.items()):
                print "  ", key, value

        return preset_dic


class WebViewAdmin(WebViewTop):
    '''Contains methods for retrieving data from the Canon WebView Settings
       pages.

       Usage Example:
           from include.webview import WebViewAdmin
           webobject = WebViewAdmin(host='web.com', username='root', \\
                                    password='bar')
           logs = webobject.AdminSysLog()
           output = open("webview_logs.txt", "w")
           output.write(logs)
           output.close()
    '''

    def AdminFileData(self, path=''):
        '''Grab the raw file data from a given file on the filesystem.'''

        params = {'path' : path}
        url_params = make_url_params(params)

        url = self.base_url + "/-wvdata-/FileData?%s" % (url_params)
        return self.grab_url(url)

    def AdminSysLog(self):
        '''Obtain the access logs of the webcam.'''

        return self.AdminFileData("/var/log/messages")

    ############################################################################
    # Return Data Functions
    ############################################################################
    def get_user_summary(self):
        '''Display the users for the month passed in.  Use 'all' for all months.'''

        results = []

        syslog = self.AdminSysLog()
        month_dict = {"Jan":1,"Feb":2,"Mar":3,"Apr":4, "May":5, "Jun":6,
                      "Jul":7,"Aug":8,"Sep":9,"Oct":10,"Nov":11,"Dec":12}
        regex = re.compile("(\w{3}) {1,2}(\d{1,2}) (\d{2}:\d{2}:\d{2}) " \
                           ".*host=(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})" \
                           ".*user=(.*), video", re.IGNORECASE)
        matches = regex.findall(syslog)

        #TODO: Deal with year soon
        for mon, day, time, ip, user in matches:
            the_user = user
            the_time = '2011-' + str(month_dict[mon]) + '-' + day + ' ' + time
            the_ip = ip
            results.append((the_user, the_time, the_ip))

        return results

class WebViewStatDB(object):
    '''Class for inserting an entry into the DB for stat tracking.  Only
       tested on a un/pw protected webcam where username shows up in the
       syslog.'''

    def __init__(self, _host, _un, _pw, _db, _table):
      '''Initially establish conneciton with DB.'''

      # Define the name of the table that will keep the stats
      self.table = _table

      try:
        import MySQLdb
        self.conn = MySQLdb.connect(host = _host,
                                    user = _un,
                                    passwd = _pw,
                                    db = _db)
        self.cursor = self.conn.cursor(MySQLdb.cursors.DictCursor)
      except MySQLdb.Error, e:
        raise Exception("Error %d: %s" % (e.args[0], e.args[1]))

# TODO: Investigate this in more depth.  I want to make sure things
#       are cleaned up okay when we're all done, but I don't want
#       this to cause the "__del__ of ignored" exception for when
#       things go wrong in __init__.  Besides, everybody says this
#       ought to be avoided.
#    def __del__(self):
#      '''Cleanup for when the object is destroyed.'''
#
#      self.cursor.close()
#      self.conn.commit()
#      self.conn.close()

    def reset_db(self):
      '''CAUTION: Will reset the database!'''

      cursor = self.cursor

      cursor.execute ("DROP TABLE IF EXISTS %s" % self.table)
      cursor.execute ("""
          CREATE TABLE %s
          (
           id int(11) NOT NULL AUTO_INCREMENT,
           user varchar(30) DEFAULT NULL,
           visited datetime DEFAULT NULL,
           ip varchar(15) DEFAULT NULL,
           PRIMARY KEY (id)
          ) ENGINE=MyISAM AUTO_INCREMENT=1 DEFAULT CHARSET=utf8
        """ % self.table)

    def add_stats_to_db(self, user, visited, ip):
      '''Will insert the user visited entry if doesn't exist'''

      cursor = self.cursor

      #FIXME:  This is a wanky solution.  I would like to be more "MySQL'ish"
      #        Doing it this way, I'm scanning throught the entire log as it's
      #        continually growing and checking one by one to see if it's already
      #        in the DB. Maybe I should keep my own log file that only keeps
      #        recently added items and throws away the rest.  Dunno...
      cursor.execute("""
          SELECT id FROM %s WHERE user='%s' AND visited='%s'
        """ % (self.table, user, visited))
      if cursor.rowcount == 0:
        cursor.execute("""
            INSERT INTO %s (user,visited,ip) VALUES ('%s','%s','%s')
          """ % (self.table, user, visited,ip))
        return True
      else:
        return False

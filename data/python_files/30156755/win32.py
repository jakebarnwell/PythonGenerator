import array
import ctypes
import struct
import threading
import win32api
import win32con
import win32gui

import time

from .. import base, events, messages
from . import exceptions

SCA_ATTACH_NOT_CONNECTED = -1
SCA_ATTACH_SUCCESS = 0
SCA_ATTACH_PENDING_AUTHORIZATION = 1
SCA_ATTACH_REFUSED = 2
SCA_ATTACH_NOT_AVAILABLE = 3

SCA_ATTACH_API_AVAILABLE = 0x8001



class _CopyData(ctypes.Structure):
    _fields_ = [
        ("dwData", ctypes.c_void_p),
        ("cbData", ctypes.c_ulong),
        ("lpData", ctypes.c_char_p),
    ]

class WinAdaptor(base.Daemon):
    """Skype API wrapper class."""

    fromSkype = None
    connected = False
    _toSkypeMsgBuffer = None

    def __init__(self):
        super(WinAdaptor, self).__init__()
        self.fromSkype = events.EventCaster()
        self._toSkypeMsgBuffer = []

    def initWin32(self):
        hInst = win32api.GetModuleHandle(None)
        self._status = SCA_ATTACH_NOT_CONNECTED
        api_attach = win32gui.RegisterWindowMessage(
            "SkypeControlAPIAttach");
        self.api_discover = api_discover = win32gui.RegisterWindowMessage(
            "SkypeControlAPIDiscover");
        wc = win32gui.WNDCLASS()
        wc.hInstance = hInst
        wc.lpfnWndProc = {
            api_attach: self._attached,
            api_discover: self._discovered,
            win32con.WM_CREATE: self._created,
            win32con.WM_COPYDATA: self._copydata,
        }
        wc.lpszClassName = className = "SkypePythonHandler"
        rc = win32gui.RegisterClass(wc)
        self._win = win32gui.CreateWindow(
            rc, "SkypePython", 0, 0, 0, 0, 0, 0, 0, hInst, None)

    def connect(self):
        """
        Connect to skype.
        """
        win32gui.SendMessageTimeout(
            win32con.HWND_BROADCAST,
            self.api_discover,
            self._win,
            win32con.SMTO_NORMAL,
            0, 5*1000
        )

    def run(self):
        self.initWin32()
        self.connect()
        while not self.connected:
            time.sleep(0.01)
        self._sendBuffer()
        win32gui.PumpMessages()

    def _created(self, hwnd, message, wparam, lparam):
        pass

    def _copydata(self, hwnd, message, wparam, lparam):
        cbs = _CopyData.from_address(lparam)
        msg = cbs.lpData
        self.fromSkype.send(msg.decode("utf-8"))
        return 1

    @property
    def connected(self):
        return self._status == 0

    def _attached(self, hwnd, message, wparam, lparam):
        self._status = lparam
        if lparam == SCA_ATTACH_SUCCESS:
            self.skypeWin = wparam
        elif lparam == SCA_ATTACH_PENDING_AUTHORIZATION:
            # Pending Authorization. what should we do?
            pass
        elif lparam == SCA_ATTACH_REFUSED:
            raise exceptions.SkypeRefusedError("Connection refused.")
        elif lparam == SCA_ATTACH_NOT_AVAILABLE:
            raise exceptions.SkypeError("API is not available.")
        elif lparam == SCA_ATTACH_API_AVAILABLE:
            # API is avaialble. what should we do?
            pass
        else:
            raise exceptions.SkypeError("Cannot handle attached event.")
        return 1

    def _discovered(self, hwnd, message, wparam, lparam):
        pass

    def _wndProc(self, hwnd, message, wparam, lparam):
        fn = self._msg_map[message]
        if fn:
            return fn(hwnd, message, wparam, lparam)
        return win32gui.DefWindowProc(hwnd, message, wparam, lparam)

    def send(self, msg):
        if self._status == SCA_ATTACH_NOT_CONNECTED:
            raise exceptions.SkypeNotConnectedError()
        elif self._status == SCA_ATTACH_PENDING_AUTHORIZATION:
            raise exceptions.SkypeNotAuthorizationError()
        elif self._status == SCA_ATTACH_REFUSED:
            raise exceptions.SkypeRefusedError()
        int_buf = array.array("L", [0])
        char_buf = array.array("c", msg + '\0')
        int_buf_addr = int_buf.buffer_info()[0]
        char_buf_addr, char_buf_size = char_buf.buffer_info()
        copy_struct = struct.pack(
            "LLL",  # dword *, dword, char *
            int_buf_addr,
            char_buf_size,
            char_buf_addr,
        )
        return win32gui.SendMessage(
            self.skypeWin, win32con.WM_COPYDATA, self._win, copy_struct)

    def _sendBuffer(self):
        assert self.connected
        while self._toSkypeMsgBuffer:
            self.send(self._toSkypeMsgBuffer.pop(0))

    @events.handler
    def toSkype(self, msg):
        if isinstance(msg, unicode):
            msg = msg.encode("utf-8")
        if self.connected:
           self.send(msg)
        else:
            self._toSkypeMsgBuffer.append(msg)

# vim: set sts=4 sw=4 et :

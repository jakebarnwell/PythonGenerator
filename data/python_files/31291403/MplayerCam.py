import os
import time
import subprocess
from signal import SIGINT
from tempfile import mkdtemp
from multiprocessing import Process, Value
from SimpleCV import FrameSource, Display, Image



# Return a sorted list of names of the entries in path
def sorted_ls(path):
    return list(sorted(os.listdir(path)))



class MplayerCamera(FrameSource):
    
    # Initialize an MplayerCamera
    def __init__(self, videoDev=1):
        
        # Temporary directory
        self._dir = mkdtemp(prefix="/dev/shm/")
        self._done = Value('b', False)
        self.__videoDev = videoDev
        self._subp = self.run_mplayer()



    def run_mplayer(self):
        
        # Device properties
        VIDEO_DEVICE='/dev/video%d'%self.__videoDev # The virtual file of the camera
        VIDEO_INPUT=2                               # The channel of the camera (0 on most machines, 2 on the PCI capture cards)
        BRIGHTNESS=-25                              # Range -100 to 100, set to zero for "normal
        CONTRAST=-25                                # See above
        HUE=0                                       #    "
        SATURATION=75                               #    "
        pstring = "/usr/bin/mplayer -really-quiet \
                   -tv driver=v4l2:device=%s:norm=PAL:input=%d:brightness=%d:contrast=%d:hue=%d:saturation=%d \
                   tv://0 \
                   -vo jpeg:outdir=%s 1> /dev/null 2>&1"\
                  %(VIDEO_DEVICE, VIDEO_INPUT, BRIGHTNESS, CONTRAST, HUE, SATURATION, self._dir)
        
        self.start_cleanup()
        return subprocess.Popen(pstring, shell=True)



    # Return a sorted list of names of the entries in _dir
    def get_list(self):
        return sorted_ls(self._dir)



    # Return the path of the most recent image
    def get_current_image_path(self):
        try:
            return os.path.join(self._dir, sorted_ls(self._dir)[-2])
        except IndexError:
            time.sleep(0.5)
            return self.get_current_image_path() # It is my party and I'll recurse if I want to.



    def kill_mplayer(self):
        self._done.value = True
        self._subp.terminate()
        self._subp.wait()
        self.cleanup_completely()



    def start_cleanup(self):
        self._done.value = False
        self._cleanup_process = Process(target=self._keep_tmpdir_clean, args=(self._done,))
        self._cleanup_process.start()



    def _keep_tmpdir_clean(self, done):
        while not done.value:
            try:
                map(lambda f: os.remove(os.path.join(self._dir, f)), self.get_list()[:-4])
            except KeyboardInterrupt:
                print "User exit"
                done.value = True



    def cleanup_completely(self):
        map(lambda f: os.remove(os.path.join(self._dir, f)), self.get_list())
        os.removedirs(self._dir)



    # Return the most recent image
    def getImage(self):
        return Image(self.get_current_image_path())



    def __del__(self):
        self.kill_mplayer()



if __name__=="__main__":
    cam = MplayerCamera()
    disp = Display()
    done = False
    while not done:
        try:
            cam.getImage().save(disp)
        except KeyboardInterrupt:
            print "User exit"
            done = True
        except Exception, e:
            print e
            done = True
    cam.kill_mplayer()
    time.sleep(0.1)




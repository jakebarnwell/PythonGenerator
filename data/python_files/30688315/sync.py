import id3reader
import chardet

import db
import dropboxapi
import storage

import shutil
import tempfile

import logging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("Sync")

class Sync(object):

    STORAGE = storage.S3Storage
    DB = db.HostingDB
    
    def __init__(self):
        self.dropbox = dropboxapi.Dropbox()
        self.db = self.DB()
        self.storage = self.STORAGE()

    def get_meta(self, fp):
        def decode_string(tag):
            for encoding in ['cp1251', 'utf-8', 'MacCyrillic']:
                try:
                    return tag.decode(encoding)
                except UnicodeDecodeError:
                    continue
            else:
                encoding = chardet.detect(tag)['encoding']
                try:
                    tag = tag.decode(encoding)
                except UnicodeDecodeError:
                    return None
                else:
                    return tag

        def decode_unicode(tag):
            try:
                tag = tag.encode('latin1')
            except UnicodeEncodeError:
                pass
            else:
                tag = decode_string(tag)
            return tag
        
        def convert(tag):
            if isinstance(tag, str):
                return decode_string(tag)
            elif isinstance(tag, unicode):
                return decode_unicode(tag)
            else:
                None
        try:
            id3r = id3reader.Reader(fp)
        except:
            log.info("Cannot read meta tag")
            return
        
        artist = convert(id3r.getValue('performer') or '')
        title = convert(id3r.getValue('title') or '')
        
        
        if artist and title:
            return {"artist":artist, "title":title}
        else:
            log.error("Bad meta tags '%s'-'%s'"%(artist, title))
            return None

    def go(self):
        files = self.dropbox.list_dropbox_directory()
        for fname in files[:5]:
            log.info("Uploading new file: '%s'"%fname)

            fp = tempfile.TemporaryFile()
            dropbox_fp = self.dropbox.get_file(fname)
            shutil.copyfileobj(dropbox_fp, fp)
            dropbox_fp.close()
            fp.seek(0)

            log.info("Reading meta")
            meta = self.get_meta(fp)
            if meta:
                log.info("Calculating content length")
                contentlength = len(fp.read())

                fp.seek(0)
                path = self.storage.upload(fp, fname)
                fp.close()

                self.db.update(path.decode("utf-8"), contentlength, meta["artist"], meta["title"])

            status = self.dropbox.remove_file(fname)
            if status:
                log.info("Deleting dropbox file: '%s'"%fname)
            else:
                log.error("Cannot delete dropbox file: '%s'"%fname)

class LocalSync(Sync):
    STORAGE = storage.S3Storage
    DB = db.LocalDB

class LocalNotebookSync(Sync):
    STORAGE = storage.LocalNotebookStorage
    DB = db.LocalNotebookDB
    
if __name__=="__main__":
    sync = LocalSync()
    sync.go()

import os
import sys

sys.path.append(os.getcwd())


def generate(path):
    import id3reader
    import guidem.model
    
    if os.access(path, os.R_OK):
        print 'Access granted'
        for root, dirs, files in os.walk(path):
            root = os.path.join(os.getcwd(), root)
            for fname in files:
                file = open(os.path.join(root, fname), 'rb')
                contentlength = os.stat(os.path.join(root, fname)).st_size
                try:
                    id3r = id3reader.Reader(file)
                except:
                    continue
                artist = (id3r.getValue('performer') or '').decode('cp1251')
                title = (id3r.getValue('title') or '').decode('cp1251')
                composition = (id3r.getValue('album') or '').decode('cp1251')
                no = id3r.getValue('track') or None
                no = int(no.split('/')[0]) if no else None
                if artist and title:
                    file = guidem.model.File(fname.decode('utf-8'), os.path.join(root, fname).decode('utf-8'), contentlength).db_add()
                    if file:
                        artist = guidem.model.Artist.get_or_add(artist)
                        if composition and no:
                            track = guidem.model.Track(title, artist, file.id, \
                                                       composition=composition, no=no).db_add()
                        else:
                            track = guidem.model.Track(title, artist, file.id).db_add()
                        if track:
                            print 'Track %s - %s added.'%(artist, track)
                        else:
                            print 'Track not added.'
                    else:
                        print "Cannot add file: '%s'"%fname
        print 'Database generated'
    else:
        print 'Access denied'    

def hosting():
    import os
    os.chdir('/usr/home/mylokin/app')
    
    from paste.deploy import appconfig
    from pylons import config
        
    from guidem.config.environment import load_environment
    
    conf = appconfig('config:/usr/home/mylokin/app/production.ini')
    load_environment(conf.global_conf, conf.local_conf)
    
    import guidem.model

        
if __name__=="__main__":
    hosting()
    generate(sys.argv[1])

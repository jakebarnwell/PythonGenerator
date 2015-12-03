import os
import urllib
import re
import threading  # get_lyrics_start starts a thread get_lyrics_thread

import gobject

import misc
import mpdhelper as mpdh
import consts
from pluginsystem import pluginsystem, BuiltinPlugin


class LyricWiki(object):
    def __init__(self):
        self.lyricServer = None

        pluginsystem.plugin_infos.append(BuiltinPlugin(
                'lyricwiki', "LyricWiki",
                "Fetch lyrics from LyricWiki.",
                {'lyrics_fetching': 'get_lyrics_start'}, self))

    def get_lyrics_start(self, *args):
        lyricThread = threading.Thread(target=self.get_lyrics_thread,
                args=args)
        lyricThread.setDaemon(True)
        lyricThread.start()

    def lyricwiki_format(self, text):
        return urllib.quote(str(unicode(text).title()))

    def lyricwiki_editlink(self, songinfo):
        artist, title = [self.lyricwiki_format(mpdh.get(songinfo, key))
                 for key in ('artist', 'title')]
        return ("http://lyricwiki.org/index.php?title=%s:%s&action=edit" %
            (artist, title))

    def get_lyrics_thread(self, callback, artist, title):
        try:
            lyricpage = urllib.urlopen('http://lyricwiki.org/index.php?'
                                       'title=%s:%s&action=edit' %
                                       (self.lyricwiki_format(artist),
                                        self.lyricwiki_format(title))).read()
            content = re.split("<textarea[^>]*>",
                    lyricpage)[1].split("</textarea>")[0]
            content = content.strip()
            redir_tag = "#redirect"
            if content[:len(redir_tag)].lower() == redir_tag:
                addr = 'http://lyricwiki.org/index.php?title=%s&action=edit' %\
                        urllib.quote(content.split("[[")[1].split("]]")[0])
                lyricpage = urllib.urlopen(addr).read()
                content = re.split("<textarea[^>]*>",
                        lyricpage)[1].split("</textarea>")[0]
                content = content.strip()
            lyrics = content.split("&lt;lyrics>")[1].split("&lt;/lyrics>")[0]
            lyrics = misc.unescape_html(lyrics)
            lyrics = misc.wiki_to_html(lyrics)
            lyrics = lyrics.decode("utf-8").replace(
                "<!-- PUT LYRICS HERE (and delete this entire line) -->",
                "Lyrics Unavailable.")
            self.call_back(callback, lyrics=lyrics)

        except:
            error = _("Fetching lyrics failed")
            self.call_back(callback, error=error)

    def call_back(self, callback, lyrics=None, error=None):
        gobject.timeout_add(0, callback, lyrics, error)

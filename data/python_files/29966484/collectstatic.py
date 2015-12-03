import os
from subprocess import call
from django.core import cache
from django.contrib.staticfiles.management.commands.collectstatic \
    import Command as CollectStaticCommand
from djangominimizer import settings
from djangominimizer.models import Minimizer
from djangominimizer.cache import Cache


# FIXME: Is it true way to override command?
class Command(CollectStaticCommand):
    def handle_noargs(self, **options):
        super(Command, self).handle_noargs(**options)

        print("\n\nNow, this will compress javascript and css files.")
        self.missing_files = 0
        self.cache = Cache()
        self.minimizer = Minimizer.objects.create()

        # YUI command template
        self.cmd_yui = 'java -jar %s -o ' % settings.COMMAND_YUI
        self.cmd_yui += '%(file_min)s %(file)s'

        # Coffee command template
        self.cmd_coffee = 'node %s -c ' % settings.COMMAND_COFFEE
        self.cmd_coffee += '%(file)s'

        # Less command template
        self.cmd_less = 'node %s -x ' % settings.COMMAND_LESS
        self.cmd_less += '%(file_name)s.less -o %(file_name)s.css'

        # compress script files.
        for script in settings.SCRIPTS:
            (name, ext) = os.path.splitext(script)
            if ext == '.coffee':
                if not settings.COFFEE_SUPPORT:
                    continue

                self.compile_script(script)

            self.compress(name, 'js')

        # then, comress style files.
        for style in settings.STYLES:
            (name, ext) = os.path.splitext(style)
            if ext == '.less':
                if not settings.LESS_SUPPORT:
                    continue

                self.compile_style(name)

            self.compress(name, 'css')

        if self.missing_files:
            print("%s file(s) not compiled. Please check these files." % \
                  self.missing_files)

    def compile_script(self, script):
        """
        Converts CoffeeScript files to Javascript files.
        """
        cmd = self.cmd_coffee % {
            'file': os.path.join(settings.SCRIPTS_PATH, script)
        }

        call(cmd.split())

    def compile_style(self, style_name):
        cmd = self.cmd_less % {
            'file_name': os.path.join(settings.STYLES_PATH, style_name)
        }

        call(cmd.split())

    def compress(self, name, ext):
        """
        Compresses scripts and styles with YUI compressor.
        """
        if ext == 'js':
            static_path = settings.SCRIPTS_PATH
        elif ext == 'css':
            static_path = settings.STYLES_PATH
        else:
            raise UnkownFileFormatException(ext)

        file_name = '%s.%s' % (name, ext)
        file_path = os.path.join(static_path, file_name)
        if not os.path.exists(file_path):
            self.missing_files += 1
            print("Missing file, %s" % file_name)

        else:
            file_min = '%s-%s.%s' % (name, self.minimizer.timestamp, ext)
            cmd = self.cmd_yui % {
                'file': file_path,
                'file_min': os.path.join(static_path, file_min)
            }

            call(cmd.split())
            print("Created, %s" % file_min)

        # update timestamp information in cache.
        self.cache.update_timestamp(self.minimizer.timestamp)

    class UnkownFileFormatException(Exception):
        def __init__(self, ext):
            self.ext = ext

        def __str__(self):
            return repr("Unkown file format: %s" % self.ext)

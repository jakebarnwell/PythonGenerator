import os
import commands
import re
import sys
from django.template.loader import render_to_string
from django.conf import settings
from file_system import File
from subprocess import check_call, CalledProcessError, STDOUT

class TemplateProcessor:
    @staticmethod
    def process(resource):
        try:
            rendered = render_to_string(resource.source_file.path, settings.CONTEXT)
            resource.source_file.write(rendered)
        except:
            print >> sys.stderr, \
            "***********************\nError while rendering page %s\n***********************" % \
            resource.url
            raise


## aym-cms code refactored into processors.
class CleverCSS:
    @staticmethod
    def process(resource):
        import clevercss
        data = resource.source_file.read_all()
        out = clevercss.convert(data)
        resource.source_file.write(out)

class HSS:
    @staticmethod
    def process(resource):
        out_file = File(resource.source_file.path_without_extension + ".css")
        hss = settings.HSS_PATH
        if not hss or not os.path.exists(hss):
            raise ValueError("HSS Processor cannot be found at [%s]" % hss)
        status, output = commands.getstatusoutput(
        u"%s %s -output %s/" % (hss, resource.source_file.path, out_file.parent.path))
        if status > 0:
            print output
            return None
        resource.source_file.delete()
        out_file.copy_to(resource.source_file.path)
        out_file.delete()

class SASS:
    @staticmethod
    def process(resource):
        out_file = File(resource.source_file.path_without_extension + ".css")
        sass = settings.SASS_PATH
        if not sass or not os.path.exists(sass):
            raise ValueError("SASS Processor cannot be found at [%s]" % sass)
        status, output = commands.getstatusoutput(
        u"%s %s %s" % (sass, resource.source_file.path, out_file))
        if status > 0:
            print output
            return None
        resource.source_file.delete()
        resource.source_file = out_file

class LessCSS:
    @staticmethod
    def process(resource):
        out_file = File(resource.source_file.path_without_extension + ".css")
        if not out_file.parent.exists:
            out_file.parent.make()
        less = settings.LESS_CSS_PATH
        if not less or not os.path.exists(less):
            raise ValueError("Less CSS Processor cannot be found at [%s]" % less)
        try:
            check_call([less, resource.source_file.path, out_file.path])
        except CalledProcessError, e:
            print 'Syntax Error when calling less'
            raise
        else:
            resource.source_file.delete()

            """
            Assign our out_file as the source_file for this resource in order for
            other processors to be able to correctly process this resource too.

            This is needed because this processor changes the extension of the source file.

            See bugreport at http://support.ringce.com/ringce/topics/lesscss_yuicompressor_fail_and_sitemap_generation_broken
            """
            resource.source_file = out_file
        if not out_file.exists:
            print 'Error Occurred when processing with Less'

class CSSPrefixer:
    @staticmethod
    def process(resource):
        import cssprefixer
        data = resource.source_file.read_all()
        out = cssprefixer.process(data, debug=False, minify=False)
        resource.source_file.write(out)

class CSSmin:
    @staticmethod
    def process(resource):
        import cssmin
        data = resource.source_file.read_all()
        out = cssmin.cssmin(data)
        resource.source_file.write(out)

class CoffeeScript:
    @staticmethod
    def process(resource):
        coffee = settings.COFFEE_PATH
        if not coffee or not os.path.exists(coffee):
            raise ValueError("CoffeeScript Processor cannot be found at [%s]" % coffee)
        status, output = commands.getstatusoutput(
        u"%s -b -c %s" % (coffee, resource.source_file.path))
        if status > 0:
            print output
            return None
        resource.source_file.delete()

class JSmin:
    @staticmethod
    def process(resource):
        import jsmin
        data = resource.source_file.read_all()
        out = jsmin.jsmin(data)
        resource.source_file.write(out)

class YUICompressor:
    @staticmethod
    def process(resource):
        if settings.YUI_COMPRESSOR == None:
            return
        compress = settings.YUI_COMPRESSOR
        if not os.path.exists(compress):
            compress = os.path.join(
                    os.path.dirname(
                    os.path.abspath(__file__)), "..", compress)

        if not compress or not os.path.exists(compress):
            raise ValueError(
            "YUI Compressor cannot be found at [%s]" % compress)

        tmp_file = File(resource.source_file.path + ".z-tmp")
        try:
            check_call(["java", "-jar", compress,
                resource.source_file.path, "-o",
                tmp_file.path])
        except CalledProcessError, e:
            print "Syntax Error when calling YUI Compressor:", e
        else:
            resource.source_file.delete()
            tmp_file.move_to(resource.source_file.path)

class ClosureCompiler:
    @staticmethod
    def process(resource):
        compress = settings.CLOSURE_COMPILER
        if not os.path.exists(compress):
            compress = os.path.join(
                    os.path.dirname(
                    os.path.abspath(__file__)), "..", compress)

        if not compress or not os.path.exists(compress):
            raise ValueError(
            "Closure Compiler cannot be found at [%s]" % compress)

        tmp_file = File(resource.source_file.path + ".z-tmp")
        try:
            check_call(["java", "-jar", compress, "--js",
                resource.source_file.path, "--js_output_file",
                tmp_file.path])
        except CalledProcessError, e:
            print "Syntax Error when calling Closure Compiler:", e
        else:
            resource.source_file.delete()
            tmp_file.move_to(resource.source_file.path)

class Thumbnail:
    @staticmethod
    def process(resource):
        from PIL import Image

        i = Image.open(resource.source_file.path)
        if i.mode != 'RGBA':
                i = i.convert('RGBA')
        i.thumbnail(
            (settings.THUMBNAIL_MAX_WIDTH, settings.THUMBNAIL_MAX_HEIGHT),
            Image.ANTIALIAS
        )

        orig_path, _, orig_extension = resource.source_file.path.rpartition('.')
        if "THUMBNAIL_FILENAME_POSTFIX" in dir(settings):
            postfix = settings.THUMBNAIL_FILENAME_POSTFIX
        else:
            postfix = "-thumb"
        thumb_path = "%s%s.%s" % (orig_path, postfix, orig_extension)

        if i.format == "JPEG" and "THUMBNAIL_JPEG_QUALITY" in dir(settings):
            i.save(thumb_path, quality = settings.THUMBNAIL_JPEG_QUALITY, optimize = True)
        else:
            i.save(thumb_path)

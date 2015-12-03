import os

from django.conf import settings
from django.core.management.base import NoArgsCommand

from ... import update


class Command(NoArgsCommand):
    help = 'Import the files in the dropbox folder into the music library.'

    def handle_noargs(self, **options):
        update.update()

        if os.listdir(settings.DROPBOX):
            self.stdout.write(
                'Some files were left in the dropbox. '
                'Please have a look to investigate.')
            self.stdout.write(
                '\nDROPBOX: %(dropbox)s\n' % {'dropbox': settings.DROPBOX})

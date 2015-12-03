import os

from django.core.management.base import BaseCommand, CommandError
from django.core.files import File
from django.contrib.auth.models import User
from django.template.defaultfilters import slugify

from rvcms.gallery.models import Album, Photo


EXTENSIONS = ('.jpg', 'jpeg', '.png', '.gif')


class Command(BaseCommand):
    """
    source_dir: The directory where the photos are located that you want to import from.
    album_name: Album name in the new gallery, this will either create a new one if needed or use an existing album.
    user_name:  Must be an existing username on the system, this user is used as the uploader of the photos.

    Note: The if the source directory contains subdirectories, they will simply not be processed.
    """
    args = '<source_dir album_name user_name>'
    help = 'Import a directory of photos into an album in the gallery.\n' + __doc__

    def handle(self, *args, **options):
        """
        Handle custom management command, checks the following:

        * The number of arguments is exactly 3
        * The source directory exists
        * The source directory contains photos
        * The user exists in the database
        * The album exists in the database, otherwise it creates the album

        It then loops through the images and calls :func:`add_photo()` for each image.
        """
        if len(args) == 3:
            source_dir, album_name, user_name = args

            # check if the source directory exists
            if os.path.exists(source_dir):
                photos = sorted([f for f in os.listdir(source_dir) if os.path.splitext(f.lower())[1] in EXTENSIONS])
                if len(photos) > 0:
                    # next thing, check if the user exists
                    try:
                        user = User.objects.get(username=user_name)
                    except User.DoesNotExist:
                        raise CommandError('User %s does not exist.' % user_name)

                    # get the album, or create it
                    try:
                        album = Album.objects.get(name=album_name)
                    except Album.DoesNotExist:
                        album = Album(name=album_name, slug=slugify(album_name), description='')
                        album.save()

                    print 'Adding to album: %s. . .' % album.name
                    for filename in photos:
                        self.add_photo(source_dir, filename, album, user)
                else:
                    raise CommandError('No images found in source directory with extension: ' + ', '.join(EXTENSIONS))
            else:
                raise CommandError('Source directory does not exist.')
        else:
            raise CommandError('3 arguments expected: ' + self.args)

    def add_photo(self, source_dir, filename, album, user):
        """
        Add photo to album.

        If a photo with the slug of the filename (without extension) already exists in the db, raise a CommandError.
        """
        title = os.path.splitext(filename)[0]
        slug = slugify(title)
        print 'Adding: %s' % filename

        try:
            photo = Photo.objects.get(slug=slug)
        except Photo.DoesNotExist:
            photo = None

        # make sure the photo isn't already in the database
        if photo is None:
            with open(os.path.join(source_dir, filename), 'r') as f:
                photo = Photo(title=title, slug=slug, description='', image=File(f), user=user)
                photo.save()
                photo.albums.add(album)   # updates automatically, no need to call save() again
        else:
            raise CommandError('The photo %s already exists in the database' % title)

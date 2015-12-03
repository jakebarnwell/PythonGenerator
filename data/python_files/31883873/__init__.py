import ImageOps
from PIL import Image
import cStringIO
import os
from flaskext.uploads import TestingFileStorage
from werkzeug.datastructures import FileStorage
from astral import app, uploads, utils

# Model
# ----------------------------------------------------------------------------

class Model(object):
    def to_dict(self):
        """
        Returns a dictionary representation of this model. Uses the
        "public_attributes" list to determine which attributes to include here.
        """
        if hasattr(self, 'public_attributes'):
            keys = getattr(self, 'public_attributes')
        elif hasattr(self, 'get_fields'):
            keys = getattr(self, 'get_fields')().keys()
        else:
            keys = ['id']

        data = dict()
        for k in keys:
            data[k] = getattr(self, k, None)
        return data


# Mixins - Provide "base" functionality shared by different model backends :P
# ----------------------------------------------------------------------------

class PhotoMixin(Model):
    """
    Provides common Photo model implementations.
    """
    public_attributes = ['id', 'title', 'caption', 'images']
    accessible_attributes = ['title', 'caption']

    def __init__(self, *args, **kwargs):
        image = kwargs.pop('image', None)
        super(PhotoMixin, self).__init__(*args, **kwargs)
        if image is not None:
            self.upload_image(image)

    def upload_image(self, original):
        self.images = {}
        if isinstance(original, FileStorage):
            self._store_image_and_transformations(original)
        elif isinstance(original, str):
            with open(original, 'r') as stream:
                self._store_image_and_transformations(TestingFileStorage(stream=stream,filename=original))
        else:
            self._store_image_and_transformations(TestingFileStorage(stream=original))

    def _store_image_and_transformations(self, original):
        self._store_image(original)
        self._store_image(original, 'thumbnail', lambda(image):ImageOps.fit(image, (260, 260), Image.ANTIALIAS))
        self._store_image(original, 'large', lambda(image):ImageOps.fit(image, (612, 612), Image.ANTIALIAS))

    def _store_image(self, original, suffix=None, transform=None):
        if self.folder is None:
            self.folder = utils.random_key(32)
        folder = self.folder

        filename = original.filename
        if suffix is not None:
            path, ext = os.path.splitext(filename)
            filename = "%s_%s%s" % (path, suffix, ext)

        original.stream.seek(0)
        original_image = Image.open(original.stream)
        original_image.filename = filename
        if callable(transform):
            transformed_image = transform(original_image)
            transformed_image.format = original_image.format
            original_image = transformed_image
        stream = cStringIO.StringIO()
        original_image.save(stream, format=original_image.format)
        stream.seek(0)

        metadata = dict()
        metadata['width'] = original_image.size[0]
        metadata['height'] = original_image.size[1]
        metadata['path'] = uploads.photos.save(FileStorage(stream=stream, filename=filename, content_type=original.content_type, headers=original.headers), folder)
        metadata['url'] = uploads.photos.url(metadata['path']) # TODO compute dynamically

        if self.images is None:
            self.images = dict()
        self.images[suffix or 'original'] = metadata

# Import the appropriate model implementations
backend = app.config.get('ASTRAL_BACKEND', 'mongo')
app.logger.info("Using backend: %s" % backend)
if backend == 'redis':
    from astral.models.redis import Photo
elif backend == 'mongo':
    from astral.models.mongo import Photo

import json
import os
from random import choice
import urlparse
import string
from PIL import Image
import cStringIO
from flaskext.uploads import TestingFileStorage
import glob
import math
import time
import astral
from astral.tests import AstralTestCase
from astral.models import Photo

# list of fixture images which are generally chosen from randomly.
images = glob.glob(os.path.join(os.path.dirname(__file__), 'fixtures', '*.jpg'))

class PhotoViewTestCase(AstralTestCase):

    # Helpers
    # --------------------------------------------------------------------------

    def create_photo(self,title='',caption='',image=None):
        """
        Creates a photo directly in the database.
        """
        with astral.app.test_request_context('/'):
            if image is None:
                image = choice(images)
            photo = Photo(title=title,caption=caption,image=image)
            photo.save()
            return photo

    # Tests
    # --------------------------------------------------------------------------

    def test_index(self):
        self.create_photo("Jabberwocky")
        self.create_photo("Foobar")

        rv = self.app.get("/api/photos/")
        assert rv.status_code == 200

        photos = json.loads(rv.data)
        titles = map(lambda p: p['title'], photos)

        assert len(photos) == 2
        assert u'Jabberwocky' in titles
        assert u'Foobar' in titles

    def test_index_empty(self):
        response = self.app.get("/api/photos/")
        photos = json.loads(response.data)
        self.assertEqual([], photos)

    def test_get(self):
        photo = self.create_photo("Lorem", "Lorem ipsum dolor.")
        response = self.app.get("/api/photos/%s/" % photo.id)
        photo_dict = json.loads(response.data)
        self.assertEquals(photo.title, photo_dict['title'])
        self.assertEquals(photo.caption, photo_dict['caption'])

    def test_get_bad_id(self):
        response = self.app.get("/api/photos/%s/" % 'nothing')
        self.assertEqual(response.status_code, 404)

    def test_post(self):
        with open(choice(images)) as file:
            rv = self.app.post("/api/photos/", data=dict(
                title='foo',
                caption='A picture of foot bread.',
                image=file
            ))

        photo_dict = json.loads(rv.data)

        assert len(photo_dict['images']) == 3
        assert 'large' in photo_dict['images']
        assert 'original' in photo_dict['images']
        assert 'thumbnail' in photo_dict['images']

        # Make sure the image files are actually being served and metadata is
        # consistent.
        for metadata in photo_dict['images'].itervalues():
            url = string.join(urlparse.urlsplit(metadata['url'])[2:]).strip()

            rv = self.app.get(url)
            assert rv.status_code == 200

            image = Image.open(cStringIO.StringIO(rv.data))
            assert metadata['width'] == image.size[0]
            assert metadata['height'] == image.size[1]

    def test_post_image_has_default_title(self):
        with open(choice(images)) as file:
            rv = self.app.post("/api/photos/", data=dict(
                image=file
            ))
            assert rv.status_code == 200
            photo_dict = json.loads(rv.data)
            assert photo_dict['title'] is not None

    def test_delete(self):
        photo = self.create_photo(title="Lorem", caption="Lorem ipsum dolor.")
        id = photo.id

        assert Photo.find_by_id(id) is not None

        rv = self.app.delete("/api/photos/%s/" % id)
        obj = json.loads(rv.data)

        assert obj == True
        assert Photo.find_by_id(id) is None

    def test_delete_bad_id(self):
        rv = self.app.delete("/api/photos/%s/" % 'nothing')
        assert rv.status_code == 404

    def test_put_form(self):
        photo = self.create_photo(title="Lorem", caption="Lorem ipsum dolor.")
        id = photo.id
        rv = self.app.put("/api/photos/%s/" % id, data={
            'title': 'Foobar',
        })
        assert rv.status_code == 200

        photo = Photo.find_by_id(id)
        self.assertEqual(photo.title, 'Foobar')

    def test_put_json(self):
        photo = self.create_photo(title="Lorem", caption="Lorem ipsum dolor.")
        id = photo.id
        rv = self.app.put("/api/photos/%s/" % id, data=json.dumps({ 'title': 'Foobar' }), content_type='application/json')
        assert rv.status_code == 200

        photo = Photo.find_by_id(id)
        assert photo.title == 'Foobar'


    def test_put_bad_id(self):
        rv = self.app.put("/api/photos/%s/" % 'nothing')
        self.assertEqual(rv.status_code, 404)

    def test_index_paging(self):
        total = 23
        limit = 7

        # Create a bunch of images, with index embedded in their title
        for i in range(total):
            self.create_photo(title="photo %d" % i)

        # Make sure only get back what we ask for
        for page in range(int(math.ceil(total/float(limit)))):
            skip = page * limit
            response = self.app.get("/api/photos/?skip=%d&limit=%d&sort=created_at" % (skip, limit))
            data = json.loads(response.data)

            # Make sure header entries are correct.
            self.assertEqual(total, int(response.headers['X-Resource-Total']))
            self.assertEqual(limit, int(response.headers['X-Resource-Limit']))
            self.assertEqual(skip, int(response.headers['X-Resource-Skip']))

            # Make sure got back the correct titles.
            titles = map((lambda x: x['title']), data)
            expected_titles = map((lambda x: u"photo %d" % (skip + x)), range(min(limit, total - skip)))
            self.assertEqual(titles, expected_titles)

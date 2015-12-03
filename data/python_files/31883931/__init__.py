import os
import inspect
from flaskext.uploads import UploadSet
from mongoalchemy.document import Document
import shutil
import astral
import unittest

class AstralTestCase(unittest.TestCase):
    def setUp(self):
        self.app = astral.app.test_client()

    def tearDown(self):
        with astral.app.test_request_context('/'):
            # Clear mongo collections.
            if hasattr(astral.models, 'mongo'):
                for name, obj in inspect.getmembers(astral.models.mongo):
                    if inspect.isclass(obj) and issubclass(obj, Document):
                        astral.models.mongo.db.session.clear_collection(obj)

            # Clear redis namespace.
            if hasattr(astral.models, 'redis'):
                r = astral.models.redis.r
                keys = r.keys("%s:*" % astral.app.config.get('REDIS_NS'))
                with r.pipeline() as pipe:
                    for key in keys:
                        pipe.delete(key)
                    pipe.execute()

            # Clear uploads.
            for name, obj in inspect.getmembers(astral.uploads):
                if isinstance(obj, UploadSet):
                    directory = os.path.abspath(obj.config.destination)
                    if os.path.exists(directory):
                        shutil.rmtree(directory)

if __name__ == '__main__':
    unittest.main()
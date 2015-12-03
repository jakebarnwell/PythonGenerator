import os
import string
from flask.globals import request
from flask.blueprints import Blueprint
from flask.templating import render_template
from astral import app
from astral.models import Photo
from astral.resources import ModelView, ResourceView

# Templates
# ------------------------------------------------------------------------------
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/test')
def jasmine():
    return render_template('test.html')

# API
# ------------------------------------------------------------------------------
class PhotoView(ModelView):
    def post(self):
        photo = self.model_class()
        self.update(photo)
        image = request.files['image']
        if photo.title is None:
            photo.title = string.capwords(os.path.splitext(os.path.basename(image.filename))[0])
        photo.upload_image(image)
        photo.save()
        return photo

api = Blueprint('api', __name__, url_prefix='/api')
PhotoView.register(api, Photo, '/photos')
app.register_blueprint(api)

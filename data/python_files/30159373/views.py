import pickle
import django.dispatch
import os
import sys
import json

from PIL import Image
from django.http import HttpResponse, HttpResponseBadRequest
from django.contrib.sessions.models import Session
from django.shortcuts import get_object_or_404, render_to_response
from django.contrib.auth.models import User
from django.template import RequestContext
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt

from product.models import Photo, Product

@csrf_exempt
def flash_login_required(function):
    """
    Decorator to recognize a user  by its session.
    Used for Flash-Uploading.
    """

    def decorator(request, *args, **kwargs):
        
        try:
            engine = __import__(settings.SESSION_ENGINE, {}, {}, [''])
        except:
            import django.contrib.sessions.backends.db
            engine = django.contrib.sessions.backends.db
        session_data = engine.SessionStore(request.POST.get('session_key'))
        user_id = session_data['_auth_user_id']
        # will return 404 if the session ID does not resolve to a valid user
        request.user = get_object_or_404(User, pk=user_id)
        return function(request, *args, **kwargs)
        
    return decorator

@flash_login_required
@csrf_exempt
def upload(request, *args, **kwargs):
    if request.method == 'POST':
        try:
            if request.FILES:
                im = Image.open(request.FILES['Filedata'])
                if 'interlace' in im.info and im.format == 'PNG' and im.info['interlace'] == 1:
                    return HttpResponse('False')
                product = Product.objects.get(id=request.POST['product_id'])
                photo = Photo(
                    original = request.FILES['Filedata'],
                    product = product
                )
                response = {}
                if photo.is_valid():
                    photo.save() #500 error after this point, something to do with the fucking response.  fix it you faggot.
                    response['success'] = True
                    return HttpResponse(json.dumps(response), mimetype="application/json")
                else:
                    response['success'] = False
                    response['error'] = 'Minimum image size is 640x480'
                    return HttpResponse(json.dumps(response), mimetype="application/json")
        except:
            import sys
            print(sys.exc_info()[0])
    return HttpResponse('hi')



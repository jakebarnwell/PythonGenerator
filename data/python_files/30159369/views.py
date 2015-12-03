import re

from django.conf import settings
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import get_template
from django.template import Context
from django.shortcuts import render_to_response
from django.template import RequestContext

from product.models import Product

def home(request):
    products = Product.objects.all()[:5]
    return render_to_response('home.html', {'products':products}, context_instance=RequestContext(request))

def deslugify(value):
    """
    Cleans up a slug by removing slug separator characters that occur at the
    beginning or end of a slug.
    """
    reverse_map = {
      "-" : " ",
    }

    for _from, _to in reverse_map.iteritems():
        value = re.sub(_from, _to, value)
    return value

def send_outbound_generic_email(recipient, title, message, template):
    try:
        email_template = get_template(template)
        email_content = email_template.render(Context({"MEDIA_URL":settings.MEDIA_URL, "message":message, "title":title, "name":recipient.first_name}))
        subject, from_email, to = title, settings.EMAIL_FROM, [recipient.email, ]
        text_content = message
        html_content = email_content
        msg = EmailMultiAlternatives(subject, text_content, from_email, [recipient.email, ], headers = {'Reply-To': settings.EMAIL_FROM})
        msg.attach_alternative(html_content, "text/html")
        msg.send()

    except Exception as e:
        pass
        #set up logging
        

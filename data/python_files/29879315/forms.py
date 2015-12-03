import datetime
from django import forms
from django.conf import settings
from django.utils.translation import ugettext_lazy as _
from django.utils.translation import ugettext_noop
from django.contrib.auth.models import User

if "notification" in settings.INSTALLED_APPS:
    from notification import models as notification
else:
    notification = None

from messages.models import Message
from messages.fields import CommaSeparatedUserField

class ComposeForm(forms.Form):
    """
    A simple default form for private messages.
    """
    recipient = forms.CharField(label=_(u"Recipient"), widget=forms.HiddenInput())
    subject = forms.CharField(label=_(u"Subject"))
    body = forms.CharField(label=_(u"Body"),
        widget=forms.Textarea(attrs={'rows': '12', 'cols':'55'}))
    r = None
    
        
    def __init__(self, *args, **kwargs):
        recipient_filter = kwargs.pop('recipient_filter', None)
        self.r = kwargs.pop('recipient', None)
        super(ComposeForm, self).__init__(*args, **kwargs)
        instance = getattr(self, 'instance', None)

        #if recipient_filter is not None:
        #    self.fields['recipient']._recipient_filter = recipient_filter
        #self.fields['recipient'].widget.attrs.update({'readonly': 'readonly', 'disabled': 'disabled'})
                
    def save(self, sender, parent_msg=None):
        r = self.cleaned_data['recipient']
        subject = self.cleaned_data['subject']
        body = self.cleaned_data['body']
        message_list = []

        r = User.objects.get(id=r)

        msg = Message(
            sender = sender,
            recipient = r,
            subject = subject,
            body = body,
        )
        if parent_msg is not None:
            msg.parent_msg = parent_msg
            parent_msg.replied_at = datetime.datetime.now()
            parent_msg.save()
        msg.save()
        message_list.append(msg)
        if notification:
            if parent_msg is not None:
                notification.send([sender], "messages_replied", {'message': msg,})
            else:
                notification.send([sender], "messages_sent", {'message': msg,})
        return message_list

import json

from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.contrib.auth import logout, authenticate, login

from account.models import Profile
from account.forms import RegistrationForm, PartnerRegistrationForm, EditProfileForm
from utils.views import send_outbound_generic_email

def rebate_signup(request):
    email = request.POST['email']
    response_data = {}
    try:
        account = Profile.objects.create(email=email, username=email)
        account.set_password('password')
        account.save()
        response_data['result'] = 'success'
        return HttpResponse(json.dumps(response_data), mimetype="application/json")
    except:
        response_data['result'] = 'fail'
        return HttpResponse(json.dumps(response_data), mimetype="application/json")
    

def ajax_login(request):
    username = request.POST['username']
    password = request.POST['password']
    user = authenticate(username=username, password=password)
    response_data = {}
    if user is not None:
        if user.is_active:
            if not request.POST.get('remember_me', None):
                request.session.set_expiry(0)
            login(request, user)
            response_data['result'] = 'success'
            return HttpResponse(json.dumps(response_data), mimetype="application/json")
        else:
            response_data['result'] = 'no_account'
            return HttpResponse(json.dumps(response_data), mimetype="application/json")
    else:
        response_data['result'] = 'fail'
        return HttpResponse(json.dumps(response_data), mimetype="application/json")

def logout(request):
    logout(request)
    return HttpResponseRedirect(reverse('home'))

def lazy_create_user(**kwargs):
    account = Profile.objects.create(email=kwargs['email'], partner=kwargs['partner'], username=kwargs['email'], first_name=kwargs['name'], address=kwargs['address'], city=kwargs['city'], state=kwargs['state'], zipcode=kwargs['zipcode'])
    account.set_password(kwargs['password'])
    account.save()
    return account
    
def register(request, pid=None):
    
    if request.method == 'POST':
        form = RegistrationForm(request.POST)

        if form.is_valid():
            new_user = form.save()
            user = Profile.objects.get(email=form.cleaned_data['email'])
            if pid:
                partner = Profile.objects.get(id=pid)
                user.partner = partner
                user.save()
            send_outbound_generic_email(
                recipient=user, 
                title="Welcome to Investaview", 
                message="Welcome to the Investaview Community. We look forward to your contributions.", #add copy to direct them to complete filling out profile 
                template="email/generic.html"
            )
            if form.cleaned_data['next']:
                return HttpResponseRedirect(form.cleaned_data['next'])
            else:
                return HttpResponseRedirect(reverse('home'))

    else:
        form = RegistrationForm()
    return render_to_response('account/register.html', {'form': form, }, context_instance=RequestContext(request))

def register_partner(request):
    if request.method == 'POST':
        form = PartnerRegistrationForm(request.POST)

        if form.is_valid():
            new_user = form.save()
            user = Profile.objects.get(email=form.cleaned_data['email'])
            send_outbound_generic_email(
                recipient=user, 
                title="Welcome to Investaview", 
                message="Welcome to Investaview.  We look forward to working with you to build our partnership.", 
                template="email/generic.html"
            )
            return HttpResponseRedirect(reverse('partner_dashboard'))

    else:
        form = PartnerRegistrationForm()
    return render_to_response('partner/registration.html', {'form': form, }, context_instance=RequestContext(request))
    
def edit_profile(request):
    """
    View allow user to edit profile
    """
    #Get profile instance to bind to form
    profile_data = Profile.objects.get(username = request.user)
    if request.method == 'POST':
        form = EditProfileForm(request.POST, request.FILES, instance=profile_data)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(request.META['HTTP_REFERER'])
    form = EditProfileForm(instance=profile_data)
    return render_to_response('account/edit_profile.html', { 'form': form, }, context_instance=RequestContext(request))


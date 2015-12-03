import hashlib
from django.core.exceptions import ObjectDoesNotExist
from django.http import Http404
from django.template.context import RequestContext
from django.template.loader import render_to_string
from django.core.mail import send_mail
from django.contrib import admin
from apogee.teamreg.models import Team

def shortlist_teams(modeladmin, request, queryset):
    if not request.user.is_superuser:
        Http404('You are not a superuser. Please do not attempt to perform unauthorized actions.')
    for team in queryset:
        event = team.event
        for member in team.members.all():
            member.shortlisted_events.add(event)
shortlist_teams.short_description = 'Shortlist selected teams'

def unshortlist_teams(modeladmin, request, queryset):
    if not request.user.is_superuser:
        Http404('You are not a superuser. Please do not attempt to perform unauthorized actions.')
    for team in queryset:
        event = team.event
        for member in team.members.all():
            member.shortlisted_events.remove(event)
unshortlist_teams.short_description = 'Unshortlist selected teams'

def finalize_teams(modeladmin, request, queryset):
    if not request.user.is_superuser:
        Http404('You are not a superuser. Please do not attempt to perform unauthorized actions.')
    for team in queryset:
        event = team.event
        for member in team.members.all():
            member.finalized_for.add(event)
            ucid = hashlib.sha224(str(member.id)).hexdigest()[:7]
            events = member.finalized_for.exclude(category__name='Workshops')
            papers = member.paperupload_set.filter(finalized=True)
            projects = member.projectupload_set.filter(finalized=True)
            workshops = member.finalized_for.filter(category__name='Workshops')
            try:
                roboarm_workshop = workshops.get(name='RoboARM Workshop')
            except ObjectDoesNotExist:
                roboarm_workshop = None
            try:
                deltawing_workshop = workshops.get(name='Delta Wing Aircraft Workshop')
            except ObjectDoesNotExist:
                deltawing_workshop = None
            email = render_to_string('email_templates/general.html',
                                     {'ucid':ucid,
                                      'participant':member,
                                      'events':events, 'papers':papers, 'projects':projects, 'workshops':workshops,
                                      'roboarm_workshop':roboarm_workshop, 'deltawing_worksop':deltawing_workshop},
                                     context_instance=RequestContext(request))
            send_mail('Apogee 2012 Confirmation', email, 'Apogee 2012 <noreply@bits-apogee.org>', [member.email])
        team.finalized = True
        team.save()
finalize_teams.short_description = 'Finalize selected teams'

def reject_teams(modeladmin, request, queryset):
    if not request.user.is_superuser:
        Http404('You are not a super user. Please do not attempt to perform unauthorized actions.')
    for team in queryset:
        team.finalized = False
        team.save()
reject_teams.short_description = 'Reject selected teams (does not reject individual members)'

class TeamAdmin(admin.ModelAdmin):
    list_display = ['event','id_tag','teamnames', 'finalized']
    filter_horizontal = ['members']
    list_filter = ['event']
    actions = [shortlist_teams, unshortlist_teams, finalize_teams, reject_teams]
    def teamnames(self, obj):
        html = ''
        for member in obj.members.all():
            html += '<li>%s</li>' % member.username
        html = '<ul>%s</ul>' % html
        return html
    teamnames.allow_tags = True
    teamnames.short_description = 'Team members'
    
    def finalise(self, request, queryset):
        rows_updated = 0
        for team in queryset:
          for participant in team.members.all():
            participant.finalized = True
            participant.shortlisted_events.add(team.event)
            participant.save()
            apid = hashlib.sha224(str(participant.id)).hexdigest()[:7]
            workshops = participant.shortlisted_events.filter(category__name = 'Workshops')
	    astro = workshops.filter(name = 'Astro Workshop')
            events = participant.shortlisted_events.exclude(category__name = 'Workshops')
            team = events.filter(is_team = True)
	    paper = events.filter(name = 'Paper Presentation')
            email = render_to_string('confirm_mail.html',{ 'p' : participant , 'id' : apid ,'workshops':workshops,'events':events,'team':team ,'paper':paper,'astro':astro })
            send_mail('Apogee 2012 Confirmation',email,'Apogee 2012 <noreply@bits-apogee.org>',['samvit.1@gmail.com'])
            rows_updated+=1
        if rows_updated == 1:
            message_bit = "1 Participant was"
        else:
            message_bit = "%s Participants were" % rows_updated
        self.message_user(request, "%s successfully finalised for Apogee 2012. Emails sent." % message_bit)
    finalise.short_description = "Mark selected as finalised"
    
    #actions = ['finalise']
    
admin.site.register(Team,TeamAdmin)

import datetime

from django.core.urlresolvers import reverse
from django.db import models
from django.db.models import Q
from django.template.defaultfilters import slugify
from django.utils.translation import ugettext, ugettext_lazy as _

from evaluations import fields
from evaluations import settings



class Template(models.Model):
    """
    A user-built evaluation.
    """

    title = models.CharField(_("Title"), max_length=50)
    # response = models.TextField(_("Response"), blank=True, 
        # help_text=_("Message user will see when evaluation is completed"),)
    start_date = models.DateField(_("Starts"))
    end_date = models.DateField(_("Ends on"))
    
    PRECEPTOR = 'P'
    STUDENT = 'S'
    SITE = LOCATION = 'L'

    TYPE_CHOICES = (
         (SITE, 'Site Evaluation'),
         (STUDENT, 'Student Evaluation'),
         (PRECEPTOR, 'Preceptor Evaluation'),
    )

    type = models.CharField(_("Type"),
        help_text=_("Type of evaluation (ie Student, Preceptor, Site)"),
        max_length=1, choices=TYPE_CHOICES,) 

    class Meta:
        verbose_name = _("Template")
        verbose_name_plural = _("Templates")

    def __unicode__(self):
        return self.title


    def total_responses(self):
        """
        Called by the admin list view where the queryset is annotated
        with the number of responses.
        """
        return self.total_responses
    total_responses.admin_order_field = "total_responses"

    @models.permalink
    def get_absolute_url(self):
        return ("view", (), {"type": self.type})

    def admin_links(self):
        view_url = self.get_absolute_url()
        responses_url = reverse("admin:form_responses", args=(self.id,))
        parts = (view_url, ugettext("View form on site"),
                 responses_url, ugettext("View Respones"))
        return "<a href='%s'>%s</a><br /><a href='%s'>%s</a>" % parts
    admin_links.allow_tags = True
    admin_links.short_description = ""
    

    def active(self):
        """
        Function to show is an evaluation is active
        """
        # return datetime.date.today()
        # return self.end_date > datetime.date.today()
        if self.start_date < datetime.date.today() and self.end_date > datetime.date.today():
            return '<img alt="True" src="/static/grappelli/img/admin/icon-yes.gif">'
        else:
            return '<img alt="True" src="/static/grappelli/img/admin/icon-yes.gif">'
    active.allow_tags = True




class Section(models.Model):
    template = models.ForeignKey("Template",related_name="templates")
    label = models.CharField(_("Label"), max_length=300)
    position = models.PositiveSmallIntegerField("Position")
    date_created = models.DateField(auto_now=False,auto_now_add=True)

    def __unicode__(self):
        return self.label



class Question(models.Model):
    """
    A field for a user-built form.
    """

    #SECTION = 1
    ##QUESTION = 2
    #element_types = (
    #    (SECTION, _("Section")),
    #    (QUESTION, _("Question")),
    #)

    section = models.ForeignKey("Section",related_name="questions")
    #element_type = models.IntegerField(_("Element Type"), choices=element_types)
    label = models.CharField(_("Label"), max_length=settings.EVALUATIONS_LABEL_MAX_LENGTH)
    field_type = models.IntegerField(_("Type"), choices=fields.NAMES, blank=True, null=True)
    required = models.BooleanField(_("Required"), default=True)
    options = models.ManyToManyField("Option", blank=True, related_name="options")
    position = models.PositiveSmallIntegerField("Position")


    class Meta:
        verbose_name = _("Question")
        verbose_name_plural = _("Questions")
        ordering = ['position']

    def __unicode__(self):
        return self.label

    def is_a(self, *args):
        """
        Helper that returns True if the field's type is given in any arg.
        """
        return self.field_type in args






class Option(models.Model):
    name = models.CharField(max_length=settings.EVALUATIONS_LABEL_MAX_LENGTH)
    value = models.CharField(max_length=settings.EVALUATIONS_LABEL_MAX_LENGTH)

    def __unicode__(self):
        return self.name + "(" + self.value + ")"

    def related_label(self):
        return u"%s (%s)" % (self.name, self.value)
    
    @staticmethod
    def autocomplete_search_fields():
        return ("value__icontains", "name__icontains",)


class Answer(models.Model):
    """
    A single field value for a response submitted via a user-built evaluation.
    """
    question = models.ForeignKey("Question")
    response = models.ForeignKey("Response")
    value = models.CharField(max_length=settings.EVALUATIONS_FIELD_MAX_LENGTH)

    class Meta:
        verbose_name = _("Answer")
        verbose_name_plural = _("Answers")


class Response(models.Model):
    """
    An response submitted via a user-built evaluation.
    """
    submit_time = models.DateTimeField(_("Date/time"))
    template = models.ForeignKey('Template', related_name='form')
    # user = models.ForeignKey(User, related_name='user')

    class Meta:
        verbose_name = _("Response")
        verbose_name_plural = _("Responses")



#class Element(models.Model):
#    form = models.ForeignKey(Template)
#    label = models.CharField(max_length=settings.EVALUATIONS_LABEL_MAX_LENGTH)
#
#    type = models.IntegerField(_("Type"),
#        choices= element_types,
#        null=True, blank=True)
#    position = models.PositiveSmallIntegerField("Position")
#
#
#class Section(Element):
#    # label = models.CharField(max_length=settings.EVALUATIONS_LABEL_MAX_LENGTH)
#    pass
#
#class Question(Element):
#    # label = models.CharField(max_length=settings.EVALUATIONS_LABEL_MAX_LENGTH)
#    field_type = models.IntegerField(_("Type"), choices=fields.NAMES)
#    required = models.BooleanField(_("Required"), default=True)
#    options = models.ManyToManyField(Option, blank=True, related_name="options")
#
#
#     

# class Section(models.Model):
#     template = models.ForeignKey("Template")  
#     name = models.CharField(max_length=settings.EVALUATIONS_LABEL_MAX_LENGTH)
#     description = models.TextField(blank=True)
#     questions = models.ManyToManyField("Question")

#     def __unicode__(self):
#         return self.name

# class Question(models.Model):
#     name = models.CharField(max_length=settings.EVALUATIONS_LABEL_MAX_LENGTH)
#     description = models.CharField(max_length=settings.EVALUATIONS_LABEL_MAX_LENGTH, blank=True)
#     field_type = models.IntegerField(_("Type"), choices=fields.NAMES)
#     options = models.ManyToManyField("Option", blank=True)
#     default = models.CharField(_("Default value"), blank=True, max_length=settings.EVALUATIONS_FIELD_MAX_LENGTH)
#     def __unicode__(self):
#         return self.name



# class PlanOfActionOption(models.Model):
#     question = models.ForeignKey(Element)  
#     name = models.CharField(max_length=settings.EVALUATIONS_LABEL_MAX_LENGTH)
#     value = models.CharField(max_length=settings.EVALUATIONS_LABEL_MAX_LENGTH)
#     options = models.ManyToManyField("Option")

#     def __unicode__(self):
#         return self.name





# class Student_Evaluation(Response):
#     # placement = models.ForeignKey("Placement")    #A placement has the student, preceptor, and site id's
#     # login_required = models.BooleanField(True)
#     pass

    
# class Preceptor_Evaluation(Response):
#     # preceptor = models.ForeignKey("Precepto")
#     # login_required = models.BooleanField(False)
#     pass

# class Site_Evaluation(Response):
#     # site = models.ForeignKey("Site")  
#     # login_required = models.BooleanField(True)
#     pass












class RelatedModel(models.Model):
    name = models.CharField(max_length=140)
    def __unicode__(self):
        return u"%s" % self.name

    def related_label(self):
        return u"%s (%s)" % (self.name, self.id)
    
    @staticmethod
    def autocomplete_search_fields():
        return ("id__iexact", "name__icontains",)


class MyModel(models.Model):
    name = models.CharField(max_length=140) 
    related_fk = models.ForeignKey(RelatedModel, verbose_name=u"Related Lookup (FK)", related_name="related_fk")
    related_m2m = models.ManyToManyField(RelatedModel, verbose_name=u"Related Lookup (M2M)", related_name="related_m2m")
    
    def __unicode__(self):
        return u"%s" % self.name






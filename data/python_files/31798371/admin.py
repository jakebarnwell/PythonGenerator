import datetime
from wilp.faculty.models import Faculty,FacultySem
from django.contrib import admin
import cStringIO as StringIO
try :
    import ho.pisa as pisa
except :
    from xhtml2pdf import pisa

from django.template.loader import get_template
from django.template import Context
from django.http import HttpResponse
from cgi import escape
from wilp.semester.models import Semester


def render_to_pdf(template_src, context_dict):
    template = get_template(template_src)
    context = Context(context_dict)
    html  = template.render(context)
    result = StringIO.StringIO()
    pdf = pisa.pisaDocument(StringIO.StringIO(html.encode("ISO-8859-1")), result)
    if not pdf.err:
        return HttpResponse(result.getvalue(), mimetype='application/pdf')
    return HttpResponse('We had some errors<pre>%s</pre>' % escape(html))

class FacultyAdmin(admin.ModelAdmin):
  list_display = ('fac_name','email','mobile','pan_no','dd','bank_acc','curr_aff')

  def gen_report(self,request,queryset):
    facs = queryset
    print request.GET
    return render_to_pdf('faculty_report.html',{'facs' : facs })
  gen_report.short_description = 'Generate report'
  
  def company_link(self,f):
    link = '<a href="/admin/company/company/'+str(f.company.id)+'/"> '+str(f.company)+" </a>"
    return link
  company_link.allow_tags = True
  company_link.short_description = 'Company'
  actions = ['gen_report']


  def save_model(self,request,obj,form,change):
    try :
      semester = Semester.objects.get(current = True)
      obj.semester = semester
    except :
      from django.contrib import messages
      messages.error(request,'No current semester is set, please contact site administrator to set the current semester.')
      self.message_user = str()
    obj.author = request.user
    obj.last_modified_by = request.user
    obj.save()
  def queryset(self , request):
    qs = super(FacultyAdmin , self).queryset(request)
    if request.user.is_superuser:
        return qs
    return qs.filter(author = request.user)

  ordering =('fac_name',)


class FacultySemAdmin(admin.ModelAdmin):
  def gen_report(self,request,queryset):
    facs = queryset
    total = 0;
    for fac in queryset:
      try:
        total+=int(fac.honorarium_final)
      except :
        pass
    
    today = datetime.datetime.now()
    company = ''
    return render_to_pdf('faculty_report.html',{'facs' : facs ,'today':today,'total':total,'company':company})
  gen_report.short_description = 'Generate report'

  actions = ['gen_report']

  change_list_template = 'report_faculty.html'
  list_display = ['faculty','honorarium','honorarium_final','company','programme','course']
  list_filter = ('company','course','programme','semester')
  list_editable = ('honorarium_final',)
admin.site.register(Faculty,FacultyAdmin)
admin.site.register(FacultySem,FacultySemAdmin)

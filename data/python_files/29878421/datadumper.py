import types
from django.contrib.auth.models import User
from django.db import models
from django.utils import simplejson as json
from django.core.serializers.json import DateTimeAwareJSONEncoder
from decimal import *

#import pyxslt.serialize
def list_difference(list1, list2):
    """uses list1 as the reference, returns list of items not in list2"""
    diff_list = []
    for item in list1:
        if not item in list2:
            diff_list.append(item)
    return diff_list

class DataDumper:
    fields = {}
    default_fields = {}
    error = int()
    expand = 2
    
    def __init__(self ,**kwargs):
        self.expand = kwargs.get('expand', 2)
        self.default_fields = kwargs.get('fields', None)
        pass
        
    def set_error(self,error):
        self.error = error

    no_expand_mode = 0
    def dump(self,data,format='json',version=1):
        """
        The main issues with django's default json serializer is that properties that
        had been added to a object dynamically are being ignored (and it also has 
        problems with some models).
        """
        
        additional_data = []
    
        def _any(data):
            ret = None
            if type(data) is types.ListType:
                ret = _list(data)
            elif type(data) is types.DictType:
                ret = _dict(data)
            elif isinstance(data, Decimal):
                # json.dumps() cant handle Decimal
                ret = smart_unicode(str(data))
            elif isinstance(data, models.query.QuerySet):
                # Actually its the same as a list ...
                ret = _list(data)
            elif isinstance(data, models.Model):
                ret = _model(data)
#            elif type(data) in types.StringTypes:
            else:
                ret = data
#            else:
#                ret = json.dumps(data)
            return ret
        
        def _model(data):
            self.expand = self.expand - 1
            if self.expand == -1:
                return None
            ret = {}
            # If we only have a model, we only want to encode the fields.
            ret["model"] = data.__class__.__name__
            if ret["model"] == "Profile":
                ret["model"] = "User"
            objType = data.__class__.__name__

            if objType == 'User':
                data = data.get_profile()
            
            if self.default_fields != None:
                self.fields[objType] = self.default_fields
            elif hasattr(data, 'export_fields') or self.expand == 0:
                if (self.expand >= 0):
                    self.fields[objType] = ('id', 'date')
                if (self.expand >= 1):
                    self.fields[objType] = self.fields[objType] + data.export_fields
                if (self.expand >= 2):
                    self.fields[objType] = self.fields[objType] + data.export_fields_ex
            else:
                raise Exception('Object %s is not serializable!' % data.__class__)
            # TODO: warto ogarnav powyzszy fragment

            fields = data._meta.fields
            for f in data._meta.fields:       
                if (self.fields[objType]) and (f.attname in self.fields[objType]):
                    attr = getattr(data, f.attname)
                    ret[f.attname] = _any(attr)

            # And additionally encode arbitrary properties that had been added.
            fields = [k.attname for k in data._meta.fields]
            add_ons = self.fields[objType]

            for k in add_ons:
                if (self.fields[objType]) and (k in self.fields[objType]):
                    if hasattr(data, k):
                        attr = getattr(data, k)
                        if callable(attr):
                            attr = attr()
                        ret[k] = _any(attr)
            self.expand = self.expand + 1

            if ret["model"] == "Photo":
                return getattr(data, "id")
            if (ret["model"] == "Business") and (self.expand == 1):
                return getattr(data, "id")

            return ret
        
        def _list(data, no_expand_mode=None):
            if no_expand_mode == None:
                no_expand_mode = self.no_expand_mode
            ret = []
            for v in data:
                if no_expand_mode:
                    ret.append(_any(v.id))
                    additional_data.append(v)
                else:
                    ret.append(_any(v))
            return ret
        
        def _dict(data):
            ret = {}
            for k,v in data.items():
                ret[k] = _any(v)
                if k == "data":
                    self.no_expand_mode = version-1
                    ret[k] = _list(v, 0)
                    ret[k] = ret[k] + _list(additional_data, 0)
                    self.no_expand_mode = 0
            return ret
        
        ret = _any(data)


        if(format == 'xml'):
            return pyxslt.serialize.toString(prettyPrintXml=False,data=ret,)
        else:
             return json.dumps(ret, cls=DateTimeAwareJSONEncoder)
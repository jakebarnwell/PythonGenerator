import xmlrpclib
import pipe
#from pypirss.cache import SimpleCache, DbCache
from helpers import get_json
from lica import DictBackend, Lica, SqliteBackend
from datetime import timedelta as td
from urllib2 import URLError
from errors import DataUnavailable
from xmlrpclib import ProtocolError

pipe.filter = pipe.where
pipe.map = pipe.select

PYPI_URL = "http://pypi.python.org/pypi"


class Package(object):
    
    def __init__(self, package_name):
        self._package_name = package_name
        self._pypi = Pypi()
        self._versions = self._fetch_data()
        
    def _fetch_data(self):
        return self._pypi.get_versions(self._package_name)
    
    @property
    def name(self):
        return self._package_name
    
    @property
    def url(self):
        return PYPI_URL + "/" + self.name
    
    @property
    def upload_time(self):
        tmp = self._versions | pipe.map(lambda v: v.upload_time) \
                             | pipe.sort(reverse=True) | pipe.first
        return tmp
    
    @property
    def versions(self):
        return self._versions


class Version(object):
    "Datastructure encapsulating the information of a version of a package"
    
    def __init__(self, package_name, version):
        '''
        :param str package_name: the package that owns the version
        :param str version: the specific version of a package
        '''
        self._package_name = package_name
        self._version = version
        self._pypi = Pypi()
        self._data = self._fetch_data()
    
    def _fetch_data(self):
        return self._pypi.get_version_info(self._package_name, self._version)
    
    @property
    def name(self):
        return self._package_name
    
    @property
    def version(self):
        return self._version
    
    @property
    def release_url(self):
        return PYPI_URL + "/{name}/{version}".format(name=self.name, 
                                                     version=self.version)
    
    @property
    def author(self):
        return self._data['info']['author']
    
    @property
    def author_email(self):
        return self._data['info']['author_email']

    @property
    def description(self):
        return self._data['info']['description']
    
    @property
    def upload_time(self):
        return self._data['urls'] | pipe.map(lambda el: el['upload_time']) \
                                  | pipe.sort \
                                  | pipe.first




class PypiProxy(object): #pragma: no cover
    __inst = None
    xmlrpc_endpoint = PYPI_URL
    json_endpoint = PYPI_URL + "/{package_name}/{version}/json"
    
    def __new__(cls):
        if cls.__inst is None:
            cls.__inst = object.__new__(cls)
        return cls.__inst
    
    def __init__(self):
        self.xmlrpc_iface = xmlrpclib.ServerProxy(self.xmlrpc_endpoint)

    
    def get_package_list(self):
        """Returns the list of existing packages in Pypi"""
        try:
            return self.xmlrpc_iface.list_packages()
        except ProtocolError:
            raise DataUnavailable()
    
    def get_versions(self, package_name):
        """Returns the list of releases for the package
        :param:`package_name` in Pypi"""
        try:
            return self.xmlrpc_iface.package_releases(package_name, True)
        except ProtocolError:
            raise DataUnavailable()

    
    def get_version_info(self, package_name, version):
        """fetches realease data for the version
        :param:`version` of the package :param:`package_name` from Pypi"""
        try:
            return get_json(self.json_endpoint.format(package_name=package_name,
                                                      version=version))
        except URLError:
            raise DataUnavailable()
    
    

    


class Pypi(object):
    __inst = None
    
    def __new__(cls):
        if cls.__inst is None:
            cls.__inst = object.__new__(cls)
        return cls.__inst
    
    def __init__(self):
        self.pypi_proxy = PypiProxy()
        self.package_list = Lica("package list", 
                                 backend=DictBackend,
                                 timespan=td(hours=12))
        self.version_info = Lica("version_infos", 
                                 backend=SqliteBackend, 
                                 path='cache/pypirss.db',
                                 timespan=0)
        self.package_versions = Lica("package_versions", 
                                     backend=SqliteBackend, 
                                     path='cache/pypirss.db',
                                     timespan=td(hours=12))
    def get_package_list(self):
        package_list, outdated = self.package_list.get('full_list',
                                                       fallback=True)
        if outdated == True:
            try:
                updated_list = self.pypi_proxy.get_package_list()
            except DataUnavailable, err:
                if package_list is None:
                    raise err
            else:
                package_list = updated_list
                self.package_list.put('full_list', updated_list)
        return package_list
    
    def package_exists(self, package_name):
        return package_name in self.get_package_list()
    
    def get_package(self, package_name):
        if self.package_exists(package_name):
            return Package(package_name)
        return None

    
    def get_versions(self, package_name):
        """Returns a list of versions for package :param:`package_name`"""
        version_list, outdated = self.package_versions.get(package_name,
                                                           fallback=True)
        if outdated == True:
            try:
                new_list = self.pypi_proxy.get_versions(package_name)
            except DataUnavailable, err:
                if version_list is None:
                    raise err
            else:
                version_list  = new_list
                self.package_versions.put(package_name, version_list)
        if version_list is None:
            version_list = []
            
        return version_list | pipe.take(10) \
                | pipe.map(lambda version: Version(package_name, version)) \
                | pipe.as_list
    
    def get_version_info(self, package_name, version):
        """Returns a Version instance with realease data for the version
        :param:`version` of the package :param:`package_name"""
        version_info = self.version_info.get(package_name, version)
            
        if version_info is None:
            version_info = self.pypi_proxy.get_version_info(package_name, 
                                                            version)
            self.version_info.put(package_name, version, version_info)
             
        return version_info
    
    




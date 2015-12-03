
import getpass

from xmlrpclib import ServerProxy, MultiCall


class MageProxy(object):

    def __init__(self, url, username, apikey=None):
        if apikey is None:
            apikey = getpass.getpass('Enter your API key: ')
        self.proxy = ServerProxy(url)
        self.sid = self.login(username, apikey)
        self._refresh_categories()
        self._refresh_products()

    def _refresh_products(self):
        self._products = set()
        for product in self.proxy.call(self.sid, 'product.list'):
            self._products.add(product['sku'])

    def _refresh_category(self, node):
        self._categories = {}
        if 'category_code' in node:
            self._categories[node['category_code']] = category_id
            for child in node['children']:
                self._add_category(node)

    def _refresh_categories(self):
        for category in self.proxy.call(self.sid, 'category.tree'):
            self._refresh_category(category)

    def login(self, username, apikey):
        return self.proxy.login(username, apikey)

    def add_or_update_product(self, sku, **kw):
        if sku in self._products:
            self.update_product(sku, **kw)
        else:
            self.add_product(sku, **kw)

    def update_product(self, sku, **kw):
        self.proxy.call(self.sid, 'product.update', [sku, kw])

    def add_product(self, sku, **kw):
        self.proxy.call(self.sid, 'product.create',
            [sku, 'simple', '4', kw])
        self._products.add(sku)

    def add_or_update_category(self, code, **kw):
        if code in self._categories:
            self.update_category(code, **kw)
        else:
            self.add_category(code, **kw)

    def update_category(self, code, **kw):
        category_id = self.get_category_id(code)
        self.proxy.call(self.sid, 'category.update', [kw])

    def add_category(self, code, **kw):
        category_id = self.proxy.call(self.sid, 'category.create', [kw])
        self._categories[code] = category_id

    def get_category_id(self, code):
        return self._categories.get(code)

    def get_category_ids(self, codes):
        return [self.get_category_id(code) for code in codes]



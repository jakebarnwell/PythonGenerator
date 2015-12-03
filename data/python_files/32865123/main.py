import cgi
import decimal
import logging
import os
import random

from google.appengine.api import users
from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import login_required
from google.appengine.ext.webapp.util import run_wsgi_app

import model
import paypal
import settings
import util

from django.utils import simplejson as json
#import json

#import os
#os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
#from google.appengine.dist import use_library
#use_library('django', '1.3')

# hack to enable urllib to work with Python 2.6
import os
#os.environ['foo_proxy'] = 'bar'
import urllib
#urllib.getproxies_macosx_sysconf = lambda: {}

class RequestHandler(webapp.RequestHandler):
    def error( self, code ):
        webapp.RequestHandler.error( self, code )
        if code >= 500 and code <= 599:
            path = os.path.join(os.path.dirname(__file__), 'templates/50x.htm')
            self.response.out.write(template.render(path, {}))
        if code == 404:
            path = os.path.join(os.path.dirname(__file__), 'templates/404.htm')
            self.response.out.write(template.render(path, {}))

class Home(RequestHandler):
    def get(self):
        data = {
            'items': model.Item.recent(),
        }
        util.add_user( self.request.uri, data )
        path = os.path.join(os.path.dirname(__file__), 'templates/main.htm')
        self.response.out.write(template.render(path, data))

class Sell(RequestHandler):
    def _process(self, message=None):
        data = { 
            'message': message,
            'items': model.Item.all().filter( 'owner =', users.get_current_user() ).fetch(100),
        }
        util.add_user( self.request.uri, data )
        path = os.path.join(os.path.dirname(__file__), 'templates/sell.htm')
        self.response.out.write(template.render(path, data))

    @login_required
    def get(self, command=None):
        self._process()

    def post(self, command):
        user = users.get_current_user()
        if not user:
            self.redirect( users.create_login_url( "/sell" ) )
        else:
            if command == 'add':
                image = self.request.get("image")
                item = model.Item( owner=user, title=self.request.get("title"), price=long( float(self.request.get("price")) * 100 ), image=db.Blob(image), enabled=True )
                item.put()
                self._process("The item was added.")
            else:
                self._process("Unsupported command.")

class Buy(RequestHandler):
    @login_required
    def get(self, key):
        item = model.Item.get(key)
        data = { 'item': item }
        util.add_user( self.request.uri, data )
        if settings.USE_EMBEDDED:
            (ok, pay) = self.start_purchase( item )
            data['endpoint'] = settings.EMBEDDED_ENDPOINT
            data['paykey'] = pay.paykey()
            path = os.path.join(os.path.dirname(__file__), 'templates/buy_embedded.htm')
        else:
            path = os.path.join(os.path.dirname(__file__), 'templates/buy.htm')
        self.response.out.write(template.render(path, data))

    def post(self, key):
        item = model.Item.get(key)
        (ok, pay) = self.start_purchase(item)
        if ok:
            self.redirect( pay.next_url().encode('ascii') ) # go to paypal
        else:
            data = {
                'item': model.Item.get(key),
                'message': 'An error occurred during the purchase process'
            }
            util.add_user( self.request.uri, data )
            path = os.path.join(os.path.dirname(__file__), 'templates/buy.htm')
            self.response.out.write(template.render(path, data))

    def start_purchase(self, item):
        purchase = model.Purchase( item=item, owner=item.owner, purchaser=users.get_current_user(), status='NEW', secret=util.random_alnum(16) )
        purchase.put()
        if settings.USE_IPN:
            ipn_url = "%s/ipn/%s/%s/" % ( self.request.host_url, purchase.key(), purchase.secret )
        else:
            ipn_url = None
        if settings.USE_CHAIN:
            seller_paypal_email = util.paypal_email(item.owner)
        else:
            seller_paypal_email = None
        pay = paypal.Pay( 
            item.price_dollars(), 
            "%sreturn/%s/%s/" % (self.request.uri, purchase.key(), purchase.secret), 
            "%scancel/%s/" % (self.request.uri, purchase.key()), 
            self.request.remote_addr,
            seller_paypal_email,
            ipn_url,
            shipping=settings.SHIPPING)
        
        logging.debug(self.request.uri)
        logging.debug(self.request.remote_addr)

        purchase.debug_request = pay.raw_request
        purchase.debug_response = pay.raw_response
        purchase.paykey = pay.paykey()
        purchase.put()
        
        if pay.status() == 'CREATED':
            purchase.status = 'CREATED'
            purchase.put()
            return (True, pay)
        else:
            purchase.status = 'ERROR'
            purchase.put()
            return (False, pay)

class BuyReturn(RequestHandler):

    def get(self, item_key, purchase_key, secret ):
        '''user arrives here after purchase'''
        purchase = model.Purchase.get( purchase_key )

        # validation
        if purchase == None: # no key
            self.error(404)

        elif purchase.status != 'CREATED' and purchase.status != 'COMPLETED':
            purchase.status_detail = 'Expected status to be CREATED or COMPLETED, not %s - duplicate transaction?' % purchase.status
            purchase.status = 'ERROR'
            purchase.put()
            self.error(501)

        elif secret != purchase.secret:
            purchase.status = 'ERROR'
            purchase.status_detail = 'BuyReturn secret "%s" did not match' % secret
            purchase.put()
            self.error(501)

        else:
            if purchase.status != 'COMPLETED':
                purchase.status = 'RETURNED'
                purchase.put()

            if settings.SHIPPING:
                purchase.shipping = paypal.ShippingAddress( purchase.paykey, self.request.remote_addr ).raw_response # TODO parse
                purchase.put()

            data = {
                'item': model.Item.get(item_key),
                'message': 'Purchased',
            }

            util.add_user( self.request.uri, data )
            
            if settings.USE_EMBEDDED:
                data['close_embedded'] = True
                data['items'] = model.Item.recent()
                path = os.path.join(os.path.dirname(__file__), 'templates/main_embedded.htm')
            else:
                path = os.path.join(os.path.dirname(__file__), 'templates/buy.htm')
            self.response.out.write(template.render(path, data))

class BuyCancel(RequestHandler):
    def get(self, item_key, purchase_key):
        logging.debug( "cancelled %s with %s" % ( item_key, purchase_key ) )
        purchase = model.Purchase.get( purchase_key )
        purchase.status = 'CANCELLED'
        purchase.put()
        data = {
            'item': model.Item.get(item_key),
            'message': 'Purchase cancelled',
        }
        util.add_user( self.request.uri, data )
        if settings.USE_EMBEDDED:
            data['close_embedded'] = True
            data['items'] = model.Item.recent()
            path = os.path.join(os.path.dirname(__file__), 'templates/main_embedded.htm')
        else:
            path = os.path.join(os.path.dirname(__file__), 'templates/buy.htm')
        self.response.out.write(template.render(path, data))

class Image (RequestHandler):
    def get(self, id):
        item = db.get(id)
        if item.image:
            self.response.headers['Content-Type'] = "image/png"
            self.response.out.write(item.image)
        else:
            self.error(404)

class Profile (RequestHandler):
    @login_required
    def get(self):
        data = {
            'profile': model.Profile.from_user(users.get_current_user())
        } 
        util.add_user( self.request.uri, data )
        path = os.path.join(os.path.dirname(__file__), 'templates/profile.htm')
        self.response.out.write(template.render(path, data))

    def post(self):
        profile = model.Profile.from_user( users.get_current_user() )
        if profile == None:
            profile = model.Profile( owner = users.get_current_user() )
        profile.paypal_email = self.request.get('paypal_email')
        profile.put()
        data = { 
            'profile': profile, 
            'message': 'Profile updated' }
        util.add_user( self.request.uri, data )
        path = os.path.join(os.path.dirname(__file__), 'templates/profile.htm')
        self.response.out.write(template.render(path, data))

class IPN (RequestHandler):

    def post(self, key, secret):
        '''incoming post from paypal'''
        logging.debug( "IPN received for %s" % key )
        ipn = paypal.IPN( self.request )
        if ipn.success():
            # request is paypal's
            purchase = model.Purchase.get( key )
            if secret != purchase.secret:
                purchase.status = 'ERROR'
                purchase.status_detail = 'IPN secret "%s" did not match' % secret
                purchase.put()
            # confirm amount
            elif purchase.item.price_decimal() != ipn.amount:
                purchase.status = 'ERROR'
                purchase.status_detail = "IPN amounts didn't match. Item price %f. Payment made %f" % ( purchase.item.price_dollars(), ipn.amount )
                purchase.put()
            else:
                purchase.status = 'COMPLETED'
                purchase.put()
        else:
            logging.info( "PayPal IPN verify failed: %s" % ipn.error )
            logging.debug( "Request was: %s" % self.request.body )

class SellHistory (RequestHandler):
    def get(self):
        data = {
            'items': model.Purchase.all().filter( 'owner =', users.get_current_user() ).order('-created').fetch(100),
        }
        util.add_user( self.request.uri, data )
        path = os.path.join(os.path.dirname(__file__), 'templates/sellhistory.htm')
        self.response.out.write(template.render(path, data))

class NotFound (RequestHandler):
    def get(self):
        self.error(404)
        
class GetBalance(RequestHandler):
    def get(self):
        self.signature_values = {
            'USER' :settings.PAYPAL_USERID,
            'PWD': settings.PAYPAL_PASSWORD,
            'SIGNATURE':settings.PAYPAL_SIGNATURE,
            'VERSION' : '51.0',
                            }
        self.API_ENDPOINT = 'https://api-3t.sandbox.paypal.com/nvp'
        self.PAYPAL_URL = 'https://www.sandbox.paypal.com/webscr&cmd=_express-checkout&token='
        self.signature = urllib.urlencode(self.signature_values) + "&"
        
        params = {
            'METHOD' : 'GetBalance'
        }
        params_string = self.signature + urllib.urlencode(params)
        self.raw_response = urllib.urlopen(self.API_ENDPOINT, params_string)
        self.response_content = self.raw_response.read()
        #self.response.out.write(self.response_content)
        res = urllib.unquote(self.response_content)
        data = dict( (n,v) for n,v in (a.split('=') for a in res.split('&') ) )

        logging.debug("get balance response was: %s" % res)
        
        path = os.path.join(os.path.dirname(__file__), 'templates/balance.htm')
        self.response.out.write(template.render(path, data))


class BuyExpress(RequestHandler):
    @login_required
    def get(self, key):
        item = model.Item.get(key)
        data = { 'item': item }
        util.add_user( self.request.uri, data )

        path = os.path.join(os.path.dirname(__file__), 'templates/buy.htm')
        self.response.out.write(template.render(path, data))

    def post(self, key):
        item = model.Item.get(key)
        (ok, next_url) = self.set_ExpressPurchase(item)
        if ok:
            self.redirect( next_url.encode('ascii') ) # go to paypal
        else:
            data = {
                'item': model.Item.get(key),
                'message': 'An error occurred during the purchase process'
            }
            util.add_user( self.request.uri, data )
            path = os.path.join(os.path.dirname(__file__), 'templates/buy.htm')
            self.response.out.write(template.render(path, data))

    def set_ExpressPurchase(self, item):
        purchase = model.Purchase( item=item, owner=item.owner, purchaser=users.get_current_user(), status='NEW', secret=util.random_alnum(16) )
        purchase.put()

        ipn_url = None

        seller_paypal_email = None
        
        returnurl = "%sreturn/%s/%s/" % (self.request.uri, purchase.key(), purchase.secret)
        cancelurl = "%scancel/%s/" % (self.request.uri, purchase.key())
        
#        pay = paypal.ExpressPay( 
#            item.price_dollars(), 
#            returnurl, 
#            cancelurl, 
#            self.request.remote_addr,
#            seller_paypal_email,
#            ipn_url,
#            shipping=settings.SHIPPING)
        
        self.signature_values = {
            'USER' :settings.PAYPAL_USERID,
            'PWD': settings.PAYPAL_PASSWORD,
            'SIGNATURE':settings.PAYPAL_SIGNATURE,
            'VERSION' : '65.0',
                            }
        self.API_ENDPOINT = 'https://api-3t.sandbox.paypal.com/nvp'
        self.PAYPAL_URL = 'https://www.sandbox.paypal.com/webscr&cmd=_express-checkout'
        self.signature = urllib.urlencode(self.signature_values) + "&"
        
        params = {
            'METHOD' : 'SetExpressCheckout'
        }
        expressParams = {
            'PAYMENTREQUEST_0_AMT' : '%0.2f' % item.price_dollars(),
            'PAYMENTREQUEST_0_CURRENCYCODE' : 'USD',
            'PAYMENTREQUEST_0_PAYMENTACTION' : 'Sale',
            'RETURNURL' : returnurl,
            'CANCELURL' : cancelurl
            }
        params_string = self.signature + urllib.urlencode(params) + "&" + urllib.urlencode(expressParams)
        
        self.raw_response = urllib.urlopen(self.API_ENDPOINT, params_string)
        self.response_content = self.raw_response.read()
        
        logging.debug(self.request.uri)
        logging.debug(self.request.remote_addr)

        data = self.API_ENDPOINT + params_string
        purchase.debug_request = json.dumps(data)
        purchase.debug_response = self.response_content
        
        res = urllib.unquote(self.response_content)
        datares = dict( (n,v) for n,v in (a.split('=') for a in res.split('&') ) )
        logging.debug(datares)
        ret_url = ""
        if datares['ACK'] == 'Success':
            purchase.paykey = datares['TOKEN']
            purchase.status = 'CREATED'
            purchase.put()
            url_red = self.PAYPAL_URL + '&token=' + purchase.paykey
            logging.info('redirect to:%s' % url_red)
            ret_url = url_red
#            secret = util.random_alnum(16)
#            method_params = {
#                'METHOD' : 'DoExpressCheckoutPayment'
#                    }
#            detail_params = {
#                'TOKEN' : purchase.paykey,
#                'PAYERID' : secret,
#                'PAYMENTREQUEST_0_AMT' : '%0.2f' % item.price_dollars(),
#                'PAYMENTREQUEST_0_CURRENCYCODE' : 'USD',
#                'PAYMENTREQUEST_0_PAYMENTACTION' : 'Sale'
#            }
#            do_exp_params_string = self.signature + urllib.urlencode(method_params) + "&" + urllib.urlencode(detail_params)
#            ret_url = self.PAYPAL_URL + "&" + do_exp_params_string
#            logging.info('redirect to:  %s' % ret_url)
            return (True, ret_url)
        else:
            return (False, ret_url)
            
class ExpressBuyReturn(RequestHandler):

    def get(self, item_key, purchase_key, secret ):
        '''user arrives here after purchase'''
        reqSrc = self.request.uri
        token_payer_id = reqSrc.split('?')[1]
        logging.info("return info: %s,%s,%s" % (item_key, purchase_key, secret))
        logging.info("token-payer-id: %s", token_payer_id)
        ret = dict( (n,v) for n,v in (a.split('=') for a in token_payer_id.split('&') ) )
        tokenID = ret['token']
        PayerID = ret['PayerID']
        logging.info("token:%s, PayerID: %s" % ( tokenID, PayerID))
        
        purchase = model.Purchase.get( purchase_key )
        item = model.Item.get(item_key)
        # validation
        if purchase == None: # no key
            self.error(404)

        elif purchase.status != 'CREATED' and purchase.status != 'COMPLETED':
            purchase.status_detail = 'Expected status to be CREATED or COMPLETED, not %s - duplicate transaction?' % purchase.status
            purchase.status = 'ERROR'
            purchase.put()
            self.error(501)

        elif secret != purchase.secret:
            purchase.status = 'ERROR'
            purchase.status_detail = 'BuyReturn secret "%s" did not match' % secret
            purchase.put()
            self.error(501)

        else:
            if purchase.status != 'COMPLETED':
                purchase.status = 'RETURNED'
                purchase.put()

            if settings.SHIPPING:
                purchase.shipping = paypal.ShippingAddress( purchase.paykey, self.request.remote_addr ).raw_response # TODO parse
                purchase.put()

            self.signature_values = {
            'USER' :settings.PAYPAL_USERID,
            'PWD': settings.PAYPAL_PASSWORD,
            'SIGNATURE':settings.PAYPAL_SIGNATURE,
            'VERSION' : '65.0',
                            }
            self.API_ENDPOINT = 'https://api-3t.sandbox.paypal.com/nvp'
            self.PAYPAL_URL = 'https://www.sandbox.paypal.com/webscr&cmd=_express-checkout'
            self.signature = urllib.urlencode(self.signature_values) + "&"
            
            params = {
                'METHOD' : 'DoExpressCheckoutPayment'
            }
            expressParams = {
                'TOKEN' : tokenID,
                'PAYERID' : PayerID,
                'PAYMENTREQUEST_0_AMT' : '%0.2f' % item.price_dollars(),
                'PAYMENTREQUEST_0_CURRENCYCODE' : 'USD',
                'PAYMENTREQUEST_0_PAYMENTACTION' : 'Sale'
                }
            params_string = self.signature + urllib.urlencode(params) + "&" + urllib.urlencode(expressParams)
            
            self.raw_response = urllib.urlopen(self.PAYPAL_URL, params_string)
            self.response_c41ontent = self.raw_response.read()
            
            logging.debug(self.request.uri)
            logging.debug(self.request.remote_addr)

            data = {
                'item': model.Item.get(item_key),
                'message': 'Purchased',
            }

            util.add_user( self.request.uri, data )
            
            path = os.path.join(os.path.dirname(__file__), 'templates/buy.htm')
            self.response.out.write(template.render(path, data))      

app = webapp.WSGIApplication( [
        ('/', Home),
        ('/sell', Sell),
        ('/sell/(.*)/', Sell),
        ('/buy/(.*)/return/([^/]*)/([^/]*)/.*', BuyReturn),
        ('/buy/(.*)/cancel/([^/]*)/.*', BuyCancel),
        ('/buy/(.*)/', Buy),
        ('/image/(.*)/', Image),
        ('/profile', Profile),
        ('/ipn/(.*)/(.*)/', IPN),
        ('/sellhistory', SellHistory),
        ('/getbalance', GetBalance),
        ('/buyexpress/(.*)/return/([^/]*)/([^/]*)/.*', ExpressBuyReturn),
        ('/buyexpress/(.*)/', BuyExpress),
        ('/.*', NotFound),
    ],
    debug=True)

def main():
    logging.getLogger().setLevel(logging.DEBUG)
    run_wsgi_app(app)

if __name__ == "__main__":
    main()
#    q = db.GqlQuery("select * from Purchase")
#    db.delete(q)
#    q = db.GqlQuery("SELECT * from Item")
#    db.delete(q)


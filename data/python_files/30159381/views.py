import stripe

from django.shortcuts import render_to_response
from django.template import RequestContext
from django.conf import settings
from django.db.models import Q
from django.contrib.contenttypes.models import ContentType
from django.http import parse_cookie

from account.views import lazy_create_user
from account.models import Profile
from product.models import Product, Photo, Order, Type, Category
from product.forms import *
from reviews import utils as reviews_utils
from reviews.views import ReviewAddForm
from uploadify.settings import UPLOADIFY_PATH, UPLOADIFY_UPLOAD_PATH
from tagging.models import Tag, TaggedItem
from utils.views import deslugify
from reviews.views import save as save_review

def order_product(request, product_id):
    product = Product.objects.get(id=product_id)
    if request.method == "POST":
        if request.user.is_authenticated():
            order_form = AuthOrderForm(request.POST)
        else:
            order_form = OrderForm(request.POST)
        if order_form.is_valid():
            token = { "number":request.POST['number'], "exp_month":request.POST['expiration_0'], "exp_year":request.POST['expiration_1'], "cvc":request.POST['ccv_number'], "name":request.POST['name'] }
            product = Product.objects.get(id=product_id)
            stripe.api_key = settings.STRIPE_API
            if request.POST['coupon']:
                coupon = request.POST['coupon']
            else:
                coupon = None
            try:
                stripe_response = stripe.Charge.create(
                    card = token,
                    amount = int(product.price*100),
                    currency = 'usd',
                    description = "%s - Product ID: %s"%(request.user.email, product.id)
                )
            except stripe.CardError, ce:
                return False, ce
        
            transaction_id = stripe_response.id
            if request.user.is_authenticated():
                account = Profile.objects.get(id=request.user.id)
            else:
                account_info = {"email":request.POST['email'], "partner":product.owner, "name":request.POST['name'], "password":request.POST['password'], "address":request.POST['address'], "city":request.POST['city'], "state":request.POST['state'], "zipcode":request.POST['zipcode']}
                account = lazy_create_user(**account_info)
            order = Order.objects.create(customer=account, transaction_id=transaction_id, product=product)
    else:
        if request.user.is_authenticated():
            order_form = AuthOrderForm()
        else:
            order_form = OrderForm()
    return render_to_response('products/order.html', {'product':product, 'order_form':order_form }, context_instance=RequestContext(request))
    
def browse_products(request):
    category = request.GET.get('category', None)
    type = request.GET.get('type', None)
    categories = Category.objects.all()
    types = Type.objects.all()
    kwargs = {
        'category__slug':category,
        'type__slug':type,
    }
    filters = dict((k,v) for k, v in kwargs.iteritems() if v is not None)
    if category or type:
        products = Product.objects.filter(**filters)
    else:
        products = Product.objects.all()
    ctype = ContentType.objects.get(model="product")
    return render_to_response('products/browse.html', {'products':products, 'types':types, 'categories':categories, 'ctype':ctype.id }, context_instance=RequestContext(request))
    
def view_product(request, slug):
    #generic product context
    product = Product.objects.get(slug=slug)
    images = Photo.objects.filter(product=product)
    average, amount = reviews_utils.get_average_for_instance(product)
    ctype = ContentType.objects.get(model="product")
    if average:
        average = (average / 5)*100
    else:
        average = 0

    #review form handling
    if request.method == "POST":
        form = ReviewAddForm(data=request.POST)
        # "Attach" the request to the form instance in order to get the user
        # out of the request within the clean method of the form (see above).
        form.request = request

        if form.is_valid():
            return save_review(request)
    else:
        form = ReviewAddForm()
    has_rated = reviews_utils.has_rated(request, product)
    tags = Tag.objects.get_for_object(product)
        
    return render_to_response('products/landing.html', {'product': product, 'images':images, 'average':average, 'amount':amount, 'ctype':ctype, "form" : form, "show_preview" : settings.REVIEWS_SHOW_PREVIEW, 'has_rated':has_rated, 'tags':tags}, context_instance=RequestContext(request))
    
def browse_by_tag(request, tag):
    tag = deslugify(tag)
    products = TaggedItem.objects.get_by_model(Product, [tag, ])
    ctype = ContentType.objects.get(model="product")
    return render_to_response('products/browse.html', {'products':products, 'ctype':ctype.id }, context_instance=RequestContext(request))
    
def browse_by_owner(request, owner):
    products = Product.objects.filter(owner=owner)
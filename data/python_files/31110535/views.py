import os
import json

from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect, HttpResponse
from django.template import RequestContext
from django.views.decorators.http import require_http_methods
from django.shortcuts import render, render_to_response

from magic_utilities.mtg.models import Card, Edition, Favorite

SCANS_EXIST = os.path.isdir(os.path.abspath(os.path.join(os.path.dirname(__file__), '../scans')))

JAVASCRIPT_FILES = [
    'jquery-1.7.1.min',
    'jquery.qtip.min',
    'jquery.jqplot.min',
    'jqplot.barRenderer.min',
    'jqplot.categoryAxisRenderer.min',
    'jq_card',
    'hooks',
    'raphael',
]

def get_user(request):
    if request.user.is_authenticated():
        return request.user
    else:
        return None

def get_current_deck(request):
    return request.session.get('current_deck', None)

@require_http_methods(["POST"])
def ajax(request):
    ''' General router for ajax requests so that we do not have to add each one to urls.py '''
    from importlib import import_module
    return_val = {'success': False, 'message': 'Your AJAX request failed.'}
    file_name = request.GET.get('sys', None)
    function_name = request.GET.get('run', None)
    whitelist = ('deck', )
    if file_name in whitelist:
        module = import_module('mtg.%s' % file_name)
        return_val = getattr(module, function_name)(request)

    return HttpResponse(json.dumps(return_val), mimetype="application/json")

@require_http_methods(["GET", "POST"])
def index(request):
    card_id = request.GET.get('id', '')
    edition_id = request.GET.get('edition_id', '')
    show = request.GET.get('show', '')
    card_type = request.GET.get('type', '')
    sub_type = request.GET.get('sub_type', '')
    rarity = request.GET.get('rarity', '')
    cost = request.GET.get('cost', '')

    if card_id:
        card = card_by_id(card_id)
        page = render(request, 'card.html', {"card": card, 'scans': SCANS_EXIST, 'js_files': JAVASCRIPT_FILES})
    elif edition_id:
        edition = Edition.objects.filter(id=edition_id)[0]
        cards = Card.objects.filter(edition=edition).all()
        page = render(request, 'edition.html', {"cards": cards, "edition": edition, 'scans': SCANS_EXIST, 'js_files': JAVASCRIPT_FILES})
    elif show == 'editions':
        editions = Edition.objects.all()
        page = render(request, 'editions_list.html', {'editions': editions, 'scans': SCANS_EXIST, 'js_files': JAVASCRIPT_FILES})
    elif card_type:
        cards = Card.objects.filter(type=card_type).all()
        page = render(request, 'cards.html', {"cards": cards, 'scans': SCANS_EXIST, 'js_files': JAVASCRIPT_FILES})
    elif sub_type:
        cards = Card.objects.filter(sub_types__contains=sub_type).all()
        page = render(request, 'cards.html', {"cards": cards, 'scans': SCANS_EXIST, 'js_files': JAVASCRIPT_FILES})
    elif rarity:
        cards = Card.objects.filter(rarity=rarity).all()
        page = render(request, 'cards.html', {"cards": cards, 'scans': SCANS_EXIST, 'js_files': JAVASCRIPT_FILES})
    elif cost:
        cards = Card.objects.filter(cost=cost).all()
        page = render(request, 'cards.html', {"cards": cards, 'scans': SCANS_EXIST, 'js_files': JAVASCRIPT_FILES})
    else:
        return show_index(request)

    return page

@require_http_methods(["GET", "POST"])
def search(request):
    search_string = request.GET.get('search_string', '')
    search_type = request.GET.get('search_type', '')
    results = []
    return_value = {
        'results': results,
        'searched': False,
        'search_string': search_string,
        'search_type': search_type,
        'scans': SCANS_EXIST
    }
    cards = []
    if search_type == 'Name':
        return_value['searched'] = True
#         cards = Card.objects.filter(name__istartswith=search_string).all()
        cards = Card.objects.filter(name__icontains=search_string).all()
    elif search_type == 'Abilities':
        return_value['searched'] = True
        cards = Card.objects.filter(abilities__icontains=search_string).all()
    elif search_type == 'Sub-Types':
        return_value['searched'] = True
        cards = Card.objects.filter(sub_types__icontains=search_string).all()
    if len(cards):
        for card in cards:
#             card = format_card(card)
            results.append(card)

    return_value['cards'] = results
    return_value['js_files'] = JAVASCRIPT_FILES
    return render(request, 'search.html', return_value)

@require_http_methods(["GET", "POST"])
def analyze(request):
    return_value = {}

    from analyze.analyzer import get_mana_curve
    from deck import current_deck

    deck = current_deck(request)
    if deck['success']:
        decklist = []
        for card in deck['cards']:
            decklist.extend([card['id']]*card['quantity'])

    # Convert our list of card ids in decklist to a list of card models.
    cards = [Card.objects.filter(pk=cid)[0] for cid in decklist]

    return_value['card_count'] = len(cards)
    return_value['mana_curve'] = get_mana_curve(cards)
    return_value['js_files'] = JAVASCRIPT_FILES
    return render(request, 'analyze.html', return_value)

@require_http_methods(['GET'])
def analyze_data_js(request):
    from analyze.analyzer import get_mana_curve, get_analyzer_test_deck_list
    from deck import current_deck

    jsonp_prefix = request.GET['jsonp']

    deck = current_deck(request)
    if deck['success']:
        decklist = []
        for card in deck['cards']:
            decklist.extend([card['id']]*card['quantity'])

    # Convert our list of card ids in decklist to a list of card models.
    cards = [Card.objects.filter(pk=cid)[0] for cid in decklist]

    mana_curve = get_mana_curve(cards)
    # Treat None as 0.
    if None in mana_curve:
        mana_curve[0] = mana_curve.pop(None)
    # Interpolate 0's into values for keys up to 9, or the maximum
    # individual card mana in the deck.
    mana_keys = mana_curve.keys()
    max_mana_interpolate = min([9] + [key for key in mana_keys if key > 9])
    for mana in xrange(0, max_mana_interpolate + 1):
        if mana not in mana_curve:
            mana_curve[mana] = 0
    # Transform from a dict to a sorted list.
    mana_curve = sorted(mana_curve.items())

    # Package it up for the client.
    mana_keys, mana_values = zip(*mana_curve) # unzip
    analysis_data_json = json.dumps(dict(
        mana_curve=mana_curve,
        mana_keys=mana_keys,
        mana_values=mana_values,
    ))

    jsonp_script = """
        $(function () {{
            {jsonp_prefix}({analysis_data_json});
        }});
    """.format(**locals())

    return HttpResponse(jsonp_script, mimetype='text/javascript')

@require_http_methods(["GET", "POST"])
def proxy(request):
    from deck import current_deck

    deck = current_deck(request)
    if deck['success']:
        decklist = []
        for card in deck['cards']:
            decklist.extend([card['id']]*card['quantity'])

    # Convert our list of card ids in decklist to a list of card models.
    cards = [Card.objects.filter(pk=cid)[0] for cid in decklist]

    return_value = {'cards': cards}
    return render(request, 'proxies.html', return_value)

def cards_by_name(name, fmt_card=True):
    cards = Card.objects.filter(name=name).all()
    if fmt_card:
        for card in cards:
            card = format_card(card)

    return cards

def card_by_id(card_id):
    card = Card.objects.filter(id=card_id)[0]
    card = format_card(card)
    return card

def create_round_robin(tournament):
    """ Generates a schedule of "fair" pairings from a list of units """
    units = TourneyPlayers.objects.filter(tournament__exact=tournament)

    if len(units) % 2:
        units.append(None)
    count    = len(units)
    sets     = sets or (count - 1)
    half     = count / 2
    schedule = []
    for turn in range(sets):
        pairings = []
        for i in range(half):
            pairings.append((units[i], units[count-i-1]))
        units.insert(1, units.pop())
        schedule.append(pairings)


def format_card(card):
    if card.legalities:
        card.legalities = json.loads(card.legalities)
    else:
        card.legalities = []

    if card.rulings:
        card.rulings = json.loads(card.rulings)
    else:
        card.rulings = []

    if card.other_side:
        card.back = Card.objects.get(id=card.other_side)

    card.other_editions = cards_by_name(card.name, fmt_card=False)
    if len(card.other_editions) == 1:
        card.other_editions = []

    return card


def random_card():
    card = Card.objects.order_by('?')[0]
    card = format_card(card)
    return card

def show_index(request):
#     user = get_user(request)
#     if user:

    card = random_card()
    return render(request, 'card.html', {"card": card, 'scans': SCANS_EXIST})

def cost_to_braces(cost):
    if len(cost) == 1:
        braces_cost = '{%s}' % str(cost)
    elif 'P' not in cost and len(cost) == 4:
        braces_cost = cost[0:2] + '/' + cost[2:]
    else:
        braces_cost = cost
    return braces_cost

def favorites(request):
    user = get_user(request)
    if not user:
        return HttpResponseRedirect("/accounts/login/")
    favorites = Favorite.objects.filter(user=user).all()
    cards = [f.card for f in favorites]
    return render(request, 'cards.html', {'cards': cards, 'js_files': JAVASCRIPT_FILES})

@require_http_methods(["GET", "POST"])
def duel(request):
    """
    Setup for the websocket dueling system.
    """

    def get_user(request):
        if request.user.is_authenticated():
            return request.user
        return 'guest'

    vars = {
        "username": get_user(request),
        'duelserver': ':8001',
        'js_files': JAVASCRIPT_FILES
    }

    return render(request, 'duel.html', vars)

@login_required
@require_http_methods(["GET", "POST"])
def profile(request):
    """
    User proflie page - display user decks & tournaments.
    """
    return render_to_response('registration/profile.html', {'js_files': JAVASCRIPT_FILES},
                              context_instance=RequestContext(request))

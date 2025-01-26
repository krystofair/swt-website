from django.shortcuts import render, redirect
from django.http import HttpResponse, HttpResponseRedirect
from django.contrib.auth import user_logged_in, user_logged_out
from django.contrib.auth.models import User
from django.views import View
from django.contrib import messages
from django.contrib.sessions.backends.db import SessionStore

from . import models
from tutu import settings
import warehouse.views as wh

import json
import logging
log = logging.getLogger("TEST_PHASE")
log.setLevel(logging.DEBUG if settings.DEBUG else logging.INFO)
log.info("start")

#import warehouse

# Create your views here.

"""
Zmienne w szablonie widoku:
  POST /order/commit
    - order.matches  # lista wybranych meczów
  POST /order/select:
    - filtermatches  # lista wyfiltrowanych meczów. POST
  POST /order/filters/:
    - filtercountries
    - filterleagues
    - seasons_from_leagues
"""

class FilterView(View):
  """Logic of filtering."""
  def post(self, request, *args, **kwargs):
    r = request
    #: here is a reassignment requirement
    ctx = dict()
    ctx |= r.session.get('state', dict())
    team = r.POST.get('team', None)
    league = r.POST.get('league', None)
    country = r.POST.get('country', None)
    season = r.POST.get('season', None)
    log.debug(f"post parameters {team=}, {league=}, {country=}, {season=}")
    if team:
      if not all([league, country]):
        ctx.update(filtermatches = wh.Matches.by_team(team))
      else:
        if league and country:
          tournament = (league, country)
          ctx.update(filtermatches = wh.Matches.by_team_in_tournament(team, tournament),
                     seasons_from_leagues = wh.Names.list_seasons_for_tournament(tournament))
    else:
      tournament = (league, country)
      if all([country, league, season]):
              ctx.update(filtermatches = wh.Matches.by_season_of_tournament(season, tournament),
                         seasons_from_leagues = wh.Names.list_seasons_for_tournament(tournament))
      elif country and league:
        ctx.update(filtermatches = wh.Matches.by_tournament(tournament),
                   seasons_from_leagues = wh.Names.list_seasons_for_tournament(tournament))
      elif country and not all([league, season]):
        ctx.update(filterleagues = wh.Names.list_leagues(country))
    log.debug(f"{ctx=}")
    #r.session['state'] = ctx    
    return render(request, 'orders/new-order.html', context=ctx)

 
class ChosenMatchesView(View):
  """Managing state of choices. This will redirect again to `/new/`."""
  def post(self, request, *args, **kwargs):
    try:
      #order_repository = models.OrderRepository.instance()
      order_id = request.session.get('order-id', None)
      state = request.session.get('state', {})
      log.debug(f"{state=}")
      new_choices = set(request.POST.getlist('choices', set()))
      log.debug(f"{new_choices=}")
      order_matches = set(state.get('order_matches', set()))
      if order := order_repository.get_order(order_id):
        order.add_match([models.Match(identifier=m) for m in order_matches])
      log.debug(f"{order_matches=}")
      order_matches |= new_choices
      state['order_matches'] = list(order_matches)
      log.debug(f"{state=}")
      request.session.modified = True
    except TypeError as e:
      log.error("Typy nie sa haszowalne które leca z wybranych meczow.")
      log.exception(e)
    except Exception as e:
      log.exception(e)
    return redirect('/order/new/')


class OrderNewView(View):
  def _load_state(self, request):
    if 'state' not in request.session:
      request.session['state'] = dict()
    return request.session['state']

  def get(self, request, *args, **kwargs):
    if 'messages' in request.session:
      del request.session['messages']
    state = self._load_state(request)
    try: del state['filtermatches']
    except KeyError: pass
    state.update(filtercountries=wh.Names.list_countries())
    return render(request, 'orders/new-order.html', context=state)

  def post(self, request, *args, **kwargs):
    state = self._load_state(request)
    matches_ids = state.get('order_matches', list())
    if not matches_ids:
      return HttpResponseRedirect('/')
    else:
      #: Build order from this matches
      #: You dont have chosen analysis view ...
      analyses.plan



def login(request, username, password):
  user: User = User.objects.get_by_natural_key(username)
  if user.check_password(password):
    user_logged_in.send(user)
    #return redirect()
    return HttpResponse("You are logged in")
  return HttpResponse("You enter wrong password")


def index(request):
  context = {}
  template = loader.get_template('orders/new-order.html')
  return HttpResponse(template.render(context, request))


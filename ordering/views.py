from django.shortcuts import render, redirect
from django.http import HttpResponse, HttpResponseRedirect
from django.contrib.auth import user_logged_in, user_logged_out
from django.contrib.auth.models import User
from django.views import View
from django.contrib import messages
from django.contrib.sessions.backends.db import SessionStore

import json
import logging
log = logging.getLogger("TEST_PHASE")
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
    log.warning(f"post parameters {team=}, {league=}, {country=}, {season=}")
    filtering = Filtering()
    if team:
      if not all([league, country, season]):
        ctx.update(filtermatches = filtering.list_team_matches(team))
      else:
        if league and country:
          ctx.update(filtermatches = filtering.list_team_matches_per_tournament(team, league, country),
                     seasons_from_leagues = filtering.list_seasons(league))
    else:
      if country and league:
        ctx.update(filtermatches = filtering.list_matches_per_tournament(league, country),
                   seasons_from_leagues = filtering.list_seasons(league))
      elif country and not all([league, season]):
        ctx.update(filterleagues = filtering.list_leagues(country))
      elif all([country, league, season]):
        ctx.update(filtermatches = filtering.list_matches_for_season_of_tournament(league, country, season),
                   seasons_from_leagues = filtering.list_seasons(league))
    r.session['state'] = ctx
    log.warning(f"{ctx=}")
    return render(request, 'ordering/new-order.html', context=ctx)
    

# TODO: 
class Filtering:
  """Filtering Service - API for searching in ordering context with warehouse dependency"""
  def list_leagues(self, country):
    """listing leagues by country, without country leagues are not listed."""
    return {'hiszpania':['la liga'], 'anglia':['premier league'], 'polska':['ekstraklasa']}.get(country, list())
  
  def list_countries(self):
    """If method has only self params it is for GET requests"""
    return ['Polska', 'Anglia', 'Szkocja', 'Irlandia', 'Hiszpania']
  
  def list_seasons(self, league):
    """seasons only per league"""
    return { "premier-league": ['22/23', '23/24', '24/25'],
      "la-liga": ['18/19', '20/21'],
      "jupiter-pro-league": ["11/12", "2024"]
    }.get(league, list())
  
  def list_team_matches(self, team):
    """ listing all matches which team played"""
    return { "chelsea": ['m1', 'm2', 'm3'],
      "machester-city": ["c1", "c3"]
    }.get(team, list())
    
  def list_matches_per_tournament(self, league, country):
    """list matches by league + country (I named it as tournament)"""
    return {
      "polska": {'ekstraklasa': list(map(str, range(1,10)))},
      "anglia": {'premier-league': list(map(str, range(10, 20)))},
      }.get(country, dict()).get(league, list())
  
  def list_matches_for_season_of_tournament(self, league, country, season):
    """name explain everything"""
    return list(map(str, range(30, 35)))
  
  def list_team_matches_per_tournament(self, team, league, country):
    matches = self.list_matches_per_tournament(league, country)
    return FilteringView._filter_matches_by_team(team, matches)
  
  @staticmethod
  def _filter_matches_by_team(team, matches):
    def f(m):
      return m if m.home == team or m.away == team else None
    return list(filter(f, matches))


class ChosenMatchesView(View):
  """Managing state of choices. This will redirect again to `/new/`."""
  def post(self, request, *args, **kwargs):
    try:
      state = request.session.get('state', {})
      log.warning(f"{state=}")
      new_choices = set(request.POST.getlist('choices', set()))
      log.warning(f"{new_choices=}")
      order_matches = set(state.get('order_matches', set()))
      log.warning(f"{order_matches=}")
      order_matches |= new_choices
      state['order_matches'] = list(order_matches)
      log.warning(f"{state=}")
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
    f=Filtering()
    state.update(filtercountries=f.list_countries())
    return render(request, 'ordering/new-order.html', context=state)
  
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
  template = loader.get_template('ordering/new-order.html')
  return HttpResponse(template.render(context, request))

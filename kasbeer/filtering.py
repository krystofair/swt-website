from django import forms
from django.forms import HiddenInput, Select
from django.utils import choices

from functools import partial
import logging

import warehouse.views as wh


EMPTY_CHOICE = [("", "?")]

MatchPromise = partial

class FilterUtilMixin:

  def logic(self, changes):
    """
        With passed changes this calculate what should be exactly updated.
        And add it to context dictionary.
        Arguments:
          changes: result form `form`.has_changes, which return names of field
    """
    ctx = dict()
    in_ = lambda x: x in changes
    # data pull out
    team = self.data['team']
    league = self.data['league']
    season = self.data['season']
    country = self.data['country']
    tournament = (league, country)
    # conditions
    leagueC = in_('league')
    countryC = in_('country')
    seasonC = in_('season')
    teamC = in_('team')
    #: Names of league, country, season are in singular for because of
    #  do things smoothly in `update` method, where key autmatically match
    #  to field name.
    if teamC:
      """ update team's games by part of text from team input (LIKE) """
      ctx.update(matches = MatchPromise(wh.Matches.by_team, team))
    elif countryC:
      """ Update leagues from this country without updating games """
      ctx.update(league = self._L())
      ctx.update(country = self._C())
    elif leagueC:
      """ Update games from tournament and update seasons for tournament"""
      ctx.update(matches = MatchPromise(wh.Matches.by_tournament, tournament))
      ctx.update(season = self._S())
      ctx.update(league = self._L())
    elif seasonC:
      """ Update games from specified season in selected tournament """
      ctx.update(matches = MatchPromise(wh.Matches.by_season_of_tournament, (season, tournament)))
      ctx.update(season = self._S())
    return ctx


  def _df(self, name):
    return self.__class__.declared_fields[name]

  def _boundF(self, x):
    return self._df(x).get_bound_field(self, x)

  def _ch(self, name):
    match name:
      case "country":
        return self._C()
      case "league":
        return self._L()
      case "season":
        return self._S()

  def _L(self, country=None):
    """
        Helper method to obtain leagues by country.
        Take country from own's form, unless passed as arguments.
    """
    if not country:
      country = self.data['country'] #  self._boundF('country').value()
    return EMPTY_CHOICE + [(l, l.title()) for l in wh.Names.list_leagues(country)]

  def _C(self):
    """Return list of countries as choices from Data API."""
    return [(c, c.title()) for c in wh.Names.list_countries()]

  def _S(self, league=None, country=None):
    """
        Helper about getting list of Seasons by country + league.
        Normally takes data from own form, but alternatively used passed.
    """
    if not league and not country:
      league = self.data['league'] # self._boundF('league').value()
      country = self.data['country'] # self._boundF('country').value()
    return (EMPTY_CHOICE +
            [(s, s) for s in
             wh.Names.list_seasons_for_tournament((league, country))]
    )

  def _recreate_field(self, field, initial=None, choices=None):
    """
        Recreate field 'field' with new initial and choices.
        Initial is for again be able to observable change.
        Choices are simply new choices which will be rendered on website.
    """
    return field.__class__(
      required=False,
      show_hidden_initial=True,
      initial=initial,
      choices = choices
    )


class FilterFormFieldId:
  """Those are identificators used in HTML template."""
  Country = 'country-filter'
  League = 'league-filter'
  Season = 'season-filter'

class FilteringForm(FilterUtilMixin, forms.Form):
  team = forms.CharField(required=False)
  country = forms.ChoiceField(show_hidden_initial=True,
                              widget=Select(attrs={'id': FilterFormFieldId.Country}))
  league = forms.ChoiceField(show_hidden_initial=True, required=False,
                             widget=Select(attrs={'id': FilterFormFieldId.League}))
  season = forms.ChoiceField(show_hidden_initial=True, required=False,
                             widget=Select(attrs={'id': FilterFormFieldId.Season}))
  matches_result_promise: MatchPromise = None
  # template_name_div = "kasbeer/filtering.html"

  def search(self):
    """Return filtered matches"""
    if self.matches_result_promise:
      return self.matches_result_promise()
    self.log.warning("Proxy for matches result not yet loaded.")
    return []

  def update(self):
    if self.has_changed():
      updates = self.logic(self.changed_data)
      for key, value in updates.items():
        match key:
          case 'league'|'season'|'country':
            #: creating new fields
            field = self._recreate_field(self._df(key), value, self._ch(key))
            #: Updating line
            self.__class__.declared_fields[key] = field
          case 'matches':
            self.matches_result_promise = value

  def __init__(self, *args, **kwargs):
    self.log = logging.getLogger("FilteringForm")
    data = args[0] if len(args) >= 1 else None
    if not data and 'data' in kwargs:
      data = kwargs.pop('data')
    if not data:
      c = self.init_country()
      l = self.init_league(c)
      s = self.init_season(l, c)
      data = {
        'country': c,
        'league': l,
        'season': s
      }
      super().__init__(data)
    else:
      super().__init__(*args, **kwargs)
      self.update()

  def init_country(self):
    all_countries = wh.Names.list_countries()
    choices = [(c, c.title()) for c in all_countries]
    self._df('country').choices = choices
    return all_countries[0]

  def init_league(self, country):
    try:
      leagues = self._L(country)
      self._df('league').choices = leagues
      return leagues[0][0]
    except Exception as e:
      self.log.exception(e)
      self.log.warning("Not update league choices in filtering")
    return ''

  def init_season(self, league, country):
    try:
      seasons = self._S(league, country)
      self._df('season').choices = seasons
    except Exception as e:
      self.log.exception(e)
      self.log.warning("Not update season choices in filtering")
      return ''
    return seasons[0][0]

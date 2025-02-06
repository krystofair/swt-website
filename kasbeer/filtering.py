from django import forms
from django.forms import HiddenInput, Select
from django.utils import choices

from functools import partial, cached_property, lru_cache
import logging

import warehouse.views as wh

logger = logging.getLogger(__name__)


EMPTY_CHOICE = [("", "?")]

Promise = partial

class DynamicChoiceField(forms.ChoiceField):

  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)

  def init(self, parent, ref, dataprovider):
    #: Parent is form which this field belongs to
    # self.parent = kwargs.pop('parent')
    self._parent = parent
    #: This is reference of value that choices depends
    # self.field_ref = kwargs.pop('field_ref')
    self._field_ref = ref  # self._conv_to_list(ref)
    #: And dataprovider is function for getting new choices
    # self.dataprovider = kwargs.pop('data_fun')
    self._data_provider = dataprovider

  # def _conv_to_list(self, value):
  #   """Helper for convert value as list of parameters"""
  #   try:
  #     if (not isinstance(value, tuple)
  #         and not isinstance(value, typing.MutableSequence)):
  #       return [value]
  #     return list(value)
  #   except:
  #     logger.warning(f"Cannot convert value {value} as list.")
  #     raise

  def _get_reference_val(self):
    """Helper for exactly get value the choices are built on."""
    logger.debug("Try get value(s) from field reference.")
    return self._parent.data[self._field_ref]

  @lru_cache(maxsize=40)
  def _ch(self, reference_value):
    """Helper to choices for could be beeing cached by dependency value."""
    logger.debug("Reading choices from data provider.")
    return self._data_provider(reference_value)

  @property
  def choices(self):
    ref_vals = self._get_reference_val()
    return self._ch(ref_val)

  @choices.setter
  def choices(self, value):
    super().choices = value


class FilterUtilMixin:

  def logic(self, changes):
    """
        With passed changes this calculate what should be exactly updated.
        And add it to context dictionary.
        Arguments:
          changes: result form `form`.has_changes, which return names of field
        Returns:
          Promise = partial for data which should be collected from API (warehouse).
    """
    ctx = dict()
    in_ = lambda x: x in changes
    # data pull out
    team = self.data.get('team', '')
    league = self.data.get('league', '')
    season = self.data.get('season', '')
    country = self.data.get('country', '')
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
      ctx.update(matches = Promise(wh.Matches.by_team, team))
    else:
      if countryC and leagueC:
        ctx.update(matches=Promise(wh.Matches.by_tournament, tournament))
        ctx.update(season=Promise(self._S, tournament))
        ctx.update(league=Promise(self._L, country))
      elif countryC:
        """ Update leagues from this country without updating games """
        ctx.update(league = Promise(self._L, country))
        ctx.update(country = Promise(self._C))
      elif leagueC:
        """ Update games from tournament and update seasons for tournament"""
        ctx.update(matches = Promise(wh.Matches.by_tournament, tournament))
        ctx.update(season = Promise(self._S, *tournament))
        ctx.update(league = Promise(self._L, country))
      elif seasonC:
        """ Update games from specified season in selected tournament """
        ctx.update(matches = Promise(wh.Matches.by_season_of_tournament, (season, tournament)))
        ctx.update(season = Promise(self._S, *tournament))
    return ctx


  def _df(self, name):
    return self.__class__.declared_fields[name]

  def _boundF(self, x):
    return self._df(x).get_bound_field(self, x)

  def _L(self, country=None):
    """
        Helper method to obtain leagues by country.
        Take country from own's form, unless passed as arguments.
    """
    if not country:
      country = self.data['country']
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

  def _recreate_field(self, field, new_choices=None):
    """
        Recreate field 'field' with new initial and choices.
        Initial is for again be able to observable change.
        Choices are simply new choices which will be rendered on website.
    """
    return field.__class__(
      required=field.required,
      show_hidden_initial=field.show_hidden_initial,
      initial=field.initial,
      choices=new_choices
    )

class FilteringForm(FilterUtilMixin, forms.Form):
  team = forms.CharField(required=False)
  country = forms.ChoiceField(show_hidden_initial=True)
  league = forms.ChoiceField(show_hidden_initial=True, required=False)
  season = forms.ChoiceField(show_hidden_initial=True, required=False)
  matches_result_promise: Promise = None
  # template_name_div = "kasbeer/filtering.html"

  def __init__(self, request, *args, **kwargs):
    logger.debug(f"{args=!r},\n\n {kwargs=!r}")
    super().__init__(*args, **kwargs)
    if not self.is_bound:
      c = self.init_country(request.session)
      l = self.init_league(c)
      s = self.init_season(l, c)
      self.initial = {
        'country': c,
        'league': l,
        'season': s
      }
    else:
      self.update()

  def search(self):
    """Return filtered matches"""
    if self.matches_result_promise:
      return self.matches_result_promise()
    logger.warning("Proxy for matches result not yet loaded.")
    return []

  def update(self):
    # if self.has_changed():
    updates = self.logic(self.changed_data)
    initial_data = {}
    for field_name, data_promise in updates.items():
      match field_name:
        case 'league'|'season'|'country':
          #: creating new fields
          field = self._recreate_field(self._df(field_name), data_promise())
          #: Updating line
          self.__class__.declared_fields[field_name] = field
          #: save initial to init whole form.
          initial_data.update({field_name: self._boundF(field_name).value()})
        case 'matches':
          self.matches_result_promise = data_promise
    self.initial = initial_data

  @lru_cache(maxsize=4)
  def init_country(self, session):
    all_countries = wh.Names.list_countries()
    choices = [(c, c.title()) for c in all_countries]
    self._df('country').choices = choices
    self._df('country').initial = all_countries[0]
    return all_countries[0]

  def init_league(self, country):
    try:
      leagues = self._L(country)
      self._df('league').choices = leagues
      self._df('league').initial = leagues[0][0]
    except Exception as e:
      logger.exception(e)
      logger.warning("Not update league choices in filtering")
      return ''
    return leagues[0][0]

  def init_season(self, league, country):
    try:
      seasons = self._S(league, country)
      self._df('season').choices = seasons
      self._df('season').initial = seasons[0][0]
    except Exception as e:
      logger.exception(e)
      logger.warning("Not update season choices in filtering")
      return ''
    return seasons[0][0]

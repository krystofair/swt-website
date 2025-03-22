"""
    Module for serving functionality about listing matches by specific
    criterion. Do not importing this by other module than forms.
"""

from django import forms
from django.forms import HiddenInput, Select
from django.utils import choices
from django.core.exceptions import ValidationError
from slugify import slugify

from functools import partial, cached_property, lru_cache
import logging
from datetime import datetime

import warehouse.views as wh

logger = logging.getLogger(__name__)


EMPTY_CHOICE = [("", "---")]

def _opt_text(value):
  """Prepare value as it should be visible to user."""
  return value.title().replace('-', ' ')

Promise = partial
"""
    Needed abstraction renamed from partial to better describe what it is doing.
    This indeed delay queries to database for specific data. It was created_at for
    be able to run logic query composition, etc and after then queries database.
"""

class FilteringHelper:

  @classmethod
  def league_choices_validator(cls, value, country):
    cls._choices_validator(value, cls.league_choices(country))

  @lru_cache()
  @staticmethod
  def country_choices():
    """Returns list of countries as choices from Data API."""
    return EMPTY_CHOICE + [(c, _opt_text(c)) for c in wh.Names.list_countries()]

  @staticmethod
  def league_choices(country):
    """
      Returns list of possible choices for league. This should be used in async
      GET request from GUI, to be consistent.
    """
    return (EMPTY_CHOICE +
            [(l, _opt_text(l)) for l in wh.Names.list_leagues(country)])

  @staticmethod
  def _choices_validator(value, choices):
    """Validate value is one of choice from choices."""
    #: Choices are in format of tuple (x, formatted_x)
    if value not in [x[0] for x in choices]:
      raise ValidationError("Not posible choice.")

  @staticmethod
  def check_slugified_value(value):
    if slugify(value) != value:
      raise ValidationError("After slugify value is different.")

  @staticmethod
  def team_name_len_validator(value):
    if len(value) < 3:
      raise ValidationError("Length of team name should be greater or equal 3.")

  @staticmethod
  def not_empty_after_slugified(value):
    if not slugify(value):
      raise ValidationError("Value is wrong.")


class FilteringForm(forms.Form):
  FOOTBALL_GAME_API_MODEL = wh.Matches.LeagueMatch

  team = forms.CharField(required=False,
                         validators=(
                           FilteringHelper.team_name_len_validator,
                           FilteringHelper.not_empty_after_slugified
                         )
  )
  # XXX: country field should be invalid when is empty, but this
  #      require changing initial value every time to not took it with
  #      team filtering then.
  country = forms.ChoiceField(show_hidden_initial=False,
                              required=False,
                              validators=(
                                FilteringHelper.check_slugified_value,
                              ),
                              choices=FilteringHelper.country_choices(),
                              widget=forms.widgets.Select(
                                attrs={"onchange": "change_country_callback(event)"}
                              )
  )
  league = forms.ChoiceField(show_hidden_initial=False,
                             required=False,
                             widget=forms.widgets.Select(
                               attrs={"id": "filtering-league-select"},
                             ),
                             validators=(
                               FilteringHelper.check_slugified_value,
                             )
  )
  # season = forms.CharField(show_hidden_initial=False, required=False,
  #                          widget=forms.widgets.Select, initial=EMPTY_CHOICE)
  matches_result_promise: Promise = None

  def __init__(self, request, *args, **kwargs):
    _initial = kwargs.pop('initial', None)
    if _initial:
      logger.warning("Passed initial wont be take into account.")
    initials = { "team": "", "country": "", "league": "" }
    super().__init__(*args, initial=initials, **kwargs)
    if self.is_bound and self.has_changed():
      ctx = self.logic(self.changed_data)
      self.matches_result_promise = ctx.get("matches", None)
      self.leagues = ctx.get('leagues', EMPTY_CHOICE)
      self.declared_fields['league'].choices = self.leagues

  def clean(self):
    """
      Extra validation for league, because this field require information
      about `country`.
    """
    try:
      if not self.has_error("country"):
        FilteringHelper.league_choices_validator(
          self.cleaned_data['league'], self.cleaned_data['country']
        )
    except:
      pass
    return super().clean()

  def logic(self, changes, model=FOOTBALL_GAME_API_MODEL):
    """
        With passed changes this calculate what should be exactly updated.
        And add it to context dictionary.
        Arguments:
          changes: result form `form`.has_changes, which return names of field
        Returns:
          Promise = partial for data which should be collected from API (warehouse).
    """
    matches_api = wh.Matches(model)
    is_changed = lambda x: x in changes
    ctx = dict()
    #: get data from form
    team = slugify(self.data.get('team', ''))
    league = self.data.get('league', '')
    country = self.data.get('country', '')
    tournament = (league, country)
    #: what was changed
    leagueC = is_changed('league')
    countryC = is_changed('country')
    teamC = is_changed('team')
    #: decision which api to use for match searching
    if teamC and countryC and leagueC:
      ctx.update(
        matches=Promise(matches_api.by_team_in_tournament, team, (league, country)),
        leagues=FilteringHelper.league_choices(country)
      )
    elif teamC and countryC:
      ctx.update(
        matches=Promise(matches_api.by_team_from_country, team, country),
        leagues=FilteringHelper.league_choices(country)
      )
    #: Names of league, country, season are in singular for because of
    #  do things smoothly in `update` method, where key autmatically match
    #  to field name.
    elif teamC:
      """ update team's games by part of text from team input (LIKE) """
      ctx.update(matches=Promise(matches_api.by_team, team))
    else:
      if countryC and leagueC:
        ctx.update(
          matches=Promise(matches_api.by_tournament, tournament),
          leagues=FilteringHelper.league_choices(country)
        )
      elif countryC:
        ctx.update(
          leagues=FilteringHelper.league_choices(country)
        )
    return ctx

  def search(self):
    """Return filtered matches"""
    if self.matches_result_promise:
      games = sorted(self.matches_result_promise(),
                     key=lambda x: x.get('when', datetime.now()))
      games.reverse()
      return games
    logger.warning("Proxy for matches result not yet loaded.")
    return []

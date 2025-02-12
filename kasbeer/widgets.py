from django import forms
from django.contrib.admin.utils import label_for_field
from django.core.exceptions import ValidationError
from django.forms import widgets

import logging
import decimal
from datetime import datetime

from .models import Match

logger = logging.getLogger(__name__)


class MatchEntryField(forms.MultiValueField):
  """Single entry at listing list."""
  DEFAULT_WEIGHT = 1.02

  def __init__(self, game=None, stats=None, **kwargs):
    if game:
      #: unpack as in order of SimpleMatch tuple
      mid, hm, aw, hmscr, awscr, *_ = game.values()
      if hmscr != game['home_score'] or mid != game['match_id']:
        raise ValueError("Getting values from match_object didn't keep order,"
                         " TODO: reimplemented.")
      INITIAL = Match(identifier=mid, weight=MatchEntryField.DEFAULT_WEIGHT)

    fields = (
      forms.BooleanField(required=False,
                         widget=MatchEntryCheckbox(self.summary(game))),
      forms.CharField(required=True, widget=widgets.HiddenInput()),
      forms.DecimalField(max_value=decimal.Decimal(2.0),
                         min_value=decimal.Decimal(-1.5),
                         step_size=decimal.Decimal(0.03),
                         required=True, widget=WeightRangeWidget())
    )

    super().__init__(
      initial=INITIAL if game else None,
      fields=fields,
      label="",
      require_all_fields=False,
      widget=MatchEntryWidget(widgets=[f.widget for f in fields]),
      **kwargs
    )

  def summary(self, game, /):
    """Creates label for checkbox."""
    if game is None:
      return "-:- - vs - - at -"
    league = game.get('league', '')
    return "{startdatetime} | {teams} {score}{league}".format(**{
      'score': "{}:{}".format(game['home_score'], game['away_score']),
      'teams': "{} vs {}".format(game['home'], game['away']),
      'startdatetime': format(
        game.get('when', datetime(1998, 4, 13)),
        "%d-%m-%Y at %H:%M"
      ),
      'league': f" | {league}" if league else ''
    })

  def clean(self, value):
    return self.compress(value)

  def compress(self, data_list):
    """Get identifier and weight of match."""
    logger.debug(f"compress({data_list})")
    ident = data_list[1]
    weight = data_list[2]
    return Match(identifier=ident, weight=weight)

class MatchEntryWidget(widgets.MultiWidget):
  use_fieldset = False

  def decompress(self, value):
    logger.debug(f"decompress({value=})")
    if isinstance(value, Match):
      return (True, value.identifier, value.weight)
    raise TypeError("Value of MatchEntry has to be models.Match!")

  def __repr__(self):
    return f"MatchEntry({self.home} <> {self.away})"

class MatchEntryCheckbox(widgets.CheckboxInput):
  template_name = 'kasbeer/widgets/win95-checkbox.html'

  def __init__(self, summary_label, check_test=None, **stats):
    """stats is:
    {
      "stat_name": { home_value, away_value },
      'another_stat_name': { home, away }
    }
    unless in future someone built Stat model specially for ease processing
    it here.
    """
    #: Attrs cutted cause of custom template.
    super().__init__(None, check_test=check_test)
    self.summary = summary_label
    #TODO: add stats processing lol

  def get_context(self, name, value, attrs):
    ctx = super().get_context(name, value, attrs)
    ctx['widget']['summary'] = self.summary
    return ctx

class WeightRangeWidget(widgets.NumberInput):
  template_name = "kasbeer/widgets/weight-range.html"
  input_type = 'range'
  attrs = {}



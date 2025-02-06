from django import forms
from django.contrib.admin.utils import label_for_field
from django.forms import widgets

import logging

from .models import Match

logger = logging.getLogger(__name__)


class MatchEntryField(forms.MultiValueField):
  """Single entry at listing list."""

  def __init__(self, mo, stats=None, **kwargs):
    #: unpack as in order of SimpleMatch tuple
    mid, hm, aw, hmscr, awscr = mo.values()
    if hmscr != mo['home_score'] or mid != mo['match_id']:
      raise ValueError("Getting values from match_object didn't keep order,"
                       " TODO: reimplemented.")
    fields = (
      forms.BooleanField(required=False,
                         widget=MatchEntryCheckbox(self.summary(mo))),
      forms.CharField(required=False, widget=widgets.HiddenInput()),
      forms.DecimalField(max_value=2.0, min_value=-1.5, step_size=0.03,
                         required=False, widget=WeightRangeWidget())
    )

    super().__init__(
      initial=Match(identifier=mid, weight=1.0),
      fields=fields,
      require_all_fields=False,
      widget=MatchEntryWidget(widgets=[f.widget for f in fields]),
      **kwargs
    )

  def summary(self, game, /):
    """Creates label for checkbox."""
    return "{score} {teams}".format(**{
      'score': "{}:{}".format(game['home_score'], game['away_score']),
      'teams': "{} vs {}".format(game['home'], game['away'])
    })

  def compress(self, data_list):
    logger.debug(f"compress({data_list})")
    ident = data_list[1]
    weight = data_list[2]
    return Match(identifier=ident, weight=weight)

class MatchEntryWidget(widgets.MultiWidget):
  #template_name = "kasbeer/widgets/match-entry.html"
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



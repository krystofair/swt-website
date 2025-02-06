from django import forms
from django.forms import widgets
from django.forms import HiddenInput, Select
from django.utils import choices

import functools
import logging

from .models import Match
from . import widgets as kasbeer_widgets
import warehouse.views as wh
from .filtering import FilteringForm

logger = logging.getLogger(__name__)

class MatchInlineEntryForm(forms.Form):
  # template_engine = 'jinja2'
  # template_name_div = 'kasbeer/widgets/match-widget.html'

  def __new__(cls, *args, **kwargs):
    """
        Arguments:
          game: Match Object from WareHouse(Data DB).
    """
    try:
      game = kwargs.pop('initial')
    except KeyError:
      logger.error("Match not passed to create entry.")
      raise
    #: type(cls) is metaclass
    new_class = type(cls).__new__(type(cls), cls.__name__,
                          bases=(forms.Form, ),
                          attrs={
                            'match': kasbeer_widgets.MatchEntryField(game,
                                                                     label="")
                          })
    return new_class(*args, **kwargs)

  # def __init__(self, mo, *args, **kwargs):
  #   """
  #       Arguments:
  #         mo: This is dict object based of SimpleMatch tuple
  #           and model of Match from WareHouse (Aleksander).
  #           So probably there has to be implemented any interface
  #           to keep it here after all. For now it's as voice contract.
  #   """
  #   super().__init__(*args, **kwargs)
  #   #: unpack as in order of SimpleMatch tuple
  #   mid, hm, aw, hmscr, awscr = mo.values()
  #   if hmscr != mo['home_score'] or mid != mo['match_id']:
  #     raise ValueError("Getting values from match_object didn't keep order,"
  #                      " TODO: reimplemented.")


  def save(self, commit=False):
    """
        Override saving from this Form to not invoke database yet.
        Because this object will be saved by "save_from_gui" method of order.
    """
    return super().save(commit)


class MatchFormSet(forms.BaseFormSet, forms.Form):
  can_delete = False
  can_order = False
  min_num = 0
  max_num = 100
  absolute_max = 100
  """Even small number will be displayed on page at once,
     So user cannot clicked at more that this number of games for sure."""
  extra = 0
  """Kasbeer do not rely on this parameters cause form has always initials."""
  form = MatchInlineEntryForm
  renderer = None

  def get_context(self):
    return super().get_context()

  def __init__(self, games, *args, **kwargs):
    super().__init__(initial=games, *args, **kwargs)

  def save_new(self, form, commit=False):
    return super().save_new(form, commit)

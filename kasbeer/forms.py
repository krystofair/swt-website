from django import forms
from django.core.exceptions import ValidationError
from django.forms import widgets
from django.forms import HiddenInput, Select
from django.utils import choices

import functools
import itertools
import logging

from .models import Match
from . import widgets as kasbeer_widgets
import warehouse.views as wh
from .filtering import FilteringForm

logger = logging.getLogger(__name__)

class MatchInlineEntryPrototype(forms.Form):
  """The mixin class to be parent for MatchInlineEntryForm."""
  # template_engine = 'jinja2'
  # match = kasbeer_widgets.MatchEntryField()

  def __init__(self, *args, **kwargs):
    #: Create this __init__ for explicitly show that this call super().__init__
    #  after our __new__.
    #: Here we should have 'data' in kwargs where form was bound
    super().__init__(*args, **kwargs)

  def save(self, commit=False):
    """
        Override saving from this Form to not invoke database yet.
        Because this object will be saved by "save_from_gui" method of order.
    """
    return super().save(commit)

  def has_changed(self):
    return True

class MatchInlineEntryForm(forms.Form):
  """
      This class has to inherit forms.Form because of type(cls) in __new__,
      where it getting metaclass of forms.Form. So then is possible to create
      itself.
  """
  def __new__(cls, *args, **kwargs):
    """
        Arguments:
          game: Match Object from WareHouse(Data DB).
    """
    game = kwargs.pop('initial', None)
    #: type(cls) is metaclass
    new_class = type(cls).__new__(type(cls), cls.__name__,
                          bases=(MatchInlineEntryPrototype, ),
                          attrs={
                            'match': kasbeer_widgets.MatchEntryField(
                              game=game,
                              stats=None
                            )
                          })
    # call __init__
    return new_class(*args, **kwargs)


class MatchFormSet(forms.BaseFormSet, forms.Form):
  can_delete = False
  can_order = False
  min_num = 0
  validate_min = False
  validate_max = True
  max_num = 100
  absolute_max = 100
  """Even small number will be displayed on page at once,
     So user cannot clicked at more that this number of games for sure."""
  extra = 0
  """Kasbeer do not rely on this parameters cause form has always initials."""
  form = MatchInlineEntryForm
  renderer = None

  def _delete_forms_not_checked(self, bound_data):
    """
        Deletes forms which was not chosen.
        And reindex it from zero.
    """
    if bound_data is None:
      return None
    try:
      data = dict(bound_data)
      logger.info(f"{data=}, {bound_data=}")
      #: Split data on these about forms and forms management + csrf.
      result_data, fg = self._split_data(data.items())
      logger.debug(f"{result_data=}, {fg=}")
      #: key_func gets form_index
      key_func = lambda x: x[0].split('-')[1]
      new_index = 0
      for group, key_value_tuples in itertools.groupby(fg, key_func):
        kvt = list(key_value_tuples)
        logger.info(f"{group=}, {kvt=}")
        if any([field == 'on' for name, field in kvt]):
          logger.debug(f"GROUP {group} is added")
          result_data.extend([self._reindex(pair, new_index) for pair in kvt])
          new_index += 1
      logger.debug(f"{result_data=}")
      data = dict(result_data)
      logger.debug(f"{data=}")
      return data
    except Exception as e:
      logger.exception(e)
      return {}

  def _split_data(self, iterable):
    def is_not_form_predicate(item):
      try: int(item[0].split('-')[1])
      except: return True
      else: return False
    not_forms_group = itertools.takewhile(is_not_form_predicate, iterable)
    forms_group = itertools.dropwhile(is_not_form_predicate, iterable)
    #: normalize value
    not_forms_group = [(k, v[0]) for k, v in not_forms_group]
    forms_group = [(k, v[0]) for k, v in forms_group]
    return not_forms_group, forms_group

  def _reindex(self, fdt, index):
    form_data_tuple = fdt
    prefix, _, field = form_data_tuple[0].split('-')
    return ('-'.join([prefix, str(index), field]), form_data_tuple[1])

  def get_context(self):
    return super().get_context()

  def __init__(self, bound_data=None, games=None, **kwargs):
    if not bound_data and not games:
      ValueError("Cannot init MatchFormSet")
    try:
      new_data = self._delete_forms_not_checked(bound_data)
    except:
      new_data = None
      logger.error("Cannot parse forms.")
    if new_data is None and not games:
      ValueError("Cannot parse forms.")
    super().__init__(initial=games, data=new_data, **kwargs)

  def save_new(self, form, commit=False):
    return super().save_new(form, commit)

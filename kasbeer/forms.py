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

  def __init__(self, *args, **kwargs):
    """
        Create this __init__ for explicitly show that this call super().__init__
        after our __new__ from MatchInlineEntryForm.
        Here we should have 'data' in kwargs where form was bound
    """
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
      This class has to inherit forms.Form because of type(cls) (cls arg in __new__),
      where it gets metaclass of forms.Form in `bases`. So then is possible to create
      itself, because Python required that hierarchy of metaclasses.
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

  def __init__(self, bound_data=None, games=None, **kwargs):
    cutted_data = None
    if not games:
      try:
        #: This change introduces `_reindex` as deprecated I think.
        cutted_data = self._delete_forms_not_checked(bound_data)
        games = self._pull_out_events(cutted_data)
        logger.info(f"MatchFormSet {cutted_data=}")
      except:
        logger.info(f"Parse forms failed. Probably no data. {bound_data=}, {games=}, {kwargs=}")
        pass
    super().__init__(initial=games, data=cutted_data, **kwargs)

  def _delete_forms_not_checked(self, bound_data):
    """
        Deletes forms which was not chosen. And reindex it from zero.
        This is because Django mechanism takes forms from set counting from
        first element is it listed out. So when User clicked only matches not
        from beggining then those choices not be taken.
        The second thing why is, I cannot parse it better in cleaning etc. So
        So I decided to cut those off from __init__, where comes all.
    """
    if bound_data is None:
      return None
    try:
      data = dict(bound_data)
      #: INFO level, for awarness about what data are in processing.
      logger.info(f"{data=}, {bound_data=}")
      #: Split data on these about forms and forms management + csrf.
      #  fg contains all forms, and result_data is from forms management.  !
      management, fg = self._split_data(data.items())
      #: result is returned as dict, but now is list for use "extend" method ease
      result = [(key, value[0]) for key, value in management]
      #: key_func gets form_index
      key_func = lambda x: x[0].split('-')[1]
      new_index = 0
      for group, key_value_tuples in itertools.groupby(fg, key_func):
        kvt = [(key, value[0]) for key, value in list(key_value_tuples)]
        logger.debug(f"{group=}, {kvt=}")
        if any([field == 'on' for _, field in kvt]):
          logger.debug(f"GROUP {group} is added")
          #: Add reindexed forms to form management stuff.
          result.extend([self._reindex(pair, new_index) for pair in kvt])
          new_index += 1
      logger.debug(f"{result=}")
      return dict(result)
    except Exception as e:
      logger.exception(e)
      return {}

  def _split_data(self, iterable):
    """
        Splits data in two parts: form management, forms. Forms are these with
        default prefix form-*.
        Returns two list of tuples (as items()).
    """
    def is_not_form_predicate(item):
      #: Differentiate form-TOTAL_FORMS and form-%d (form-0, form-1, ...)
      try: int(item[0].split('-')[1])
      except: return True
      else: return False
    not_forms_group = itertools.takewhile(is_not_form_predicate, iterable)
    forms_group = itertools.dropwhile(is_not_form_predicate, iterable)
    #: normalize value
    not_forms_group = [(k, v) for k, v in not_forms_group]
    forms_group = [(k, v) for k, v in forms_group]
    return not_forms_group, forms_group

  def _reindex(self, fdt, index):
    """That is 'form-5' change to 'form-0' etc."""
    form_data_tuple = fdt
    prefix, _, field = form_data_tuple[0].split('-')
    return ('-'.join([prefix, str(index), field]), form_data_tuple[1])

  def _pull_out_events(self, data, model=wh.Matches.LeagueMatch):
    """Gets matches from WareHouse by ids."""
    #: Split data on these about forms and forms management + csrf.
    management, forms = self._split_data(data.items())
    match_ids = [value for key, value in forms if key.endswith('match_1')]
    logger.debug(f"<_pull_out_events>: {management=}, {forms=}, {match_ids=}")
    api = wh.Matches(model)
    return api.by_ids(match_ids)


class CommitOrderForm(forms.Form):
  """Simplify form to add summary to order."""
  summary = forms.CharField(max_length=64)
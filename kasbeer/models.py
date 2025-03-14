#: Third party imports
from django.db import models
from django.contrib.auth.models import User
from django.contrib.sessions.models import Session
import pandas
import attrs
try:
  import orjson as jsonlib
except:
  import json as jsonlib

#: built-ins imports
import importlib
import logging
from functools import partialmethod
import uuid
from datetime import datetime

#: project imports
from m2.tasks import collect_tasks, prepare_choices_tasks, ANALYSES_MODULE
from m2 import api as m2_api


# Create your models here.

logger = logging.getLogger(__name__)

class Order(models.Model):
  draft = models.BooleanField(default=False)
  """User can save order as undone yet."""
  complete = models.BooleanField(default=False)
  created_at = models.DateTimeField(verbose_name="creation datetime",
                                    auto_now=True)
  user = models.ForeignKey(User, on_delete=models.CASCADE)
  summary = models.CharField(max_length=64, blank=True, null=True)
  """Every order belongs to some user after saved."""
  # object = models.Manager()  # default manager

  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self._jobs = list()
    self._matches = list()
    self.log = logging.getLogger("orders")

  @property
  def matches(self):
    if not self._matches:
      try:
        self._matches = self.match_set.all()
      except ValueError:
        return []
      except Exception as e:
        logger.exception(e)
    return self._matches

  @matches.setter
  def matches(self, value):
    order.append(value)

  @property
  def jobs(self):
    if not self._jobs:
      try:
        self._jobs = self.job_set.all()
      except ValueError:
        return []
      except Exception as e:
        logger.exception(e)
    return self._jobs

  @jobs.setter
  def jobs(self, value):
    self.append(value)

  def __str__(self):
    compl = '✅️' if self.complete else '🔜️'
    d = ' DRAFT' if self.draft else ''
    creat = format(self.created_at, "%d/%m/%Yt%H:%M:%S")
    return f"Order({creat},{self.summary}) {compl}{d}"

  def __repr__(self):
    return (f"Order({self.id})")

  def append(self, value):
    """
        Add object to order with type it can served.
        Raises TypeError when appending object isn't served by order.
    """
    match value:
      case Job():
        self._jobs.append(value)
      case Match():
        for m in self._matches:
          if m.identifier == value.identifier:
            #: Only update weight in match
            m.weight = value.weight
            break
        else:
          self._matches.append(value)
      case _:
        logger.warning("Tried of append {} of type {}".format(value, type(value)))

  def remove(self, value):
    """
        Opposite to append. See `Order::append`.
    """
    try:
      match value:
        case Job():
          self._jobs.remove(value)
        case Match():
          self._matches.remove(value)
    except ValueError:
      self.log.warning("Try of removing item not on list."
                       "Not important, but something is bad designed.")

  def validate(self, raise_exception=False):
    if len(self.jobs) == 0 or len(self.matches) == 0:
      if raise_exception:
        raise ValueError("Order has to have at least one analysis and one match")
      return False
    return True

  def set_complete(self):
    self.complete = True
    super().save(update_fields=['complete'])

  def save(self, **kwargs):
    if not self.draft:
      #TODO: Should be handled by showing modal to client. With info.
      self.validate(raise_exception=True)
    #: Actual saving
    #: First save order
    super().save(**kwargs)
    #: Saving related objects with setting parent.
    for j in self.jobs:
      if self.user.has_perm("add_analysis", j.analysis()):
        j.order = self
        j.save()
    for m in self.matches:
      m.order = self
      m.save()
    if not self.draft:
      #: Use M2 app for plan processing order.
      try:
        m2_api.plan(self)
      except TimeoutError as e:
        self.log.error("Order saved, but {}".format(str(e)))
        raise ValueError("Something goes wrong, notify admin.")

  def save_as_draft(self):
    """For action to save order for later as a draft, cause user don't see checkbox with [x]draft."""
    self.draft = True
    self.save()

  def clone(self):
    new_order = Order(draft=True)
    new_order.matches = self.matches.copy()
    new_order.jobs = self.jobs.copy()
    return new_order


class Match(models.Model):
  """This is like Value Object"""
  class Meta:
    verbose_name_plural = "matches"
  identifier = models.CharField(max_length=32)
  weight = models.DecimalField(max_digits=5, decimal_places=2)
  order = models.ForeignKey(Order, on_delete=models.CASCADE)

  def __repr__(self):
    return f"kasbeer.Match({self.identifier}, {self.weight})"


class Analysis(models.Model):
  """Managed objects by admin <-> tasks functions."""
  class Meta:
    verbose_name_plural = "analyses"
    #: This permissions are per objects, so that is why not plural form is used.
    permissions = [("run_analysis", "Can calculate analysis by job")]

  name = models.CharField(primary_key=True, max_length=128)
  #: After add task in `tasks` module, you have to run "makemigrations"
  task_func = models.CharField(max_length=128,
                               choices=prepare_choices_tasks(collect_tasks()),
                               verbose_name="Name")
  description = models.TextField(null=True, blank=True,
                                 help_text="Left this field empty for auto fill"
                                           " with __doc__ from task function.")

  def save(self, **kwargs):
    """Save Analysis with automatically setting name in it."""
    try:
      t = self.task()
      desc = ' '.join(t.__doc__.strip().split('\n'))
      desc = ' '.join(filter(None, desc.split(' ')))
      self.name = t.__analysis_name__
      if self.description == "":
        self.description = desc
      super().save(**kwargs)
    except:
      raise

  def __repr__(self):
    return f"Analysis<{self.task_func}>"

  def __str__(self):
    return self.name

  def task(self):
    """Returns function from python code as code. This task could be called."""
    tasks = importlib.import_module(ANALYSES_MODULE)
    if hasattr(tasks, self.task_func):
      return getattr(tasks, self.task_func)
    raise ValueError("This analysis has not implementation or name of function `task_func` is wrong.")


class Job(models.Model):
  """
      Analysis in order, is this should be as a `proxy model`? #XXX
  """
  order = models.ForeignKey(Order, on_delete=models.CASCADE)
  analysis_name = models.CharField(max_length=128, choices=[(t['name'], t['name']) for t in collect_tasks()])
  result = models.JSONField(null=True, blank=True)
  error = models.CharField(max_length=512, blank=True, null=True)
  #: There is better method for doing this - converting field, solution for short time.
  df = None

  def analysis(self):
    """Get Analysis by name correlation."""
    return Analysis.objects.get(name = self.analysis_name)

  def dataframe(self):
    return pandas.DataFrame.from_dict(self.result)

  def save(self, **kwargs):
    """Save method overrided for auto converting from dataframe"""
    #: If df (dataframe) is initialized, so object probably
    if self.df is not None:
      if isinstance(self.df, pandas.DataFrame):
        self.result = self.df.to_json()
        self.df = None
    super(Job, self).save(**kwargs)

  def __repr__(self):
    return "<Job({}) = {}>".format(self.analysis_name, self.result or "...")


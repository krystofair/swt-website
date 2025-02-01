#: Third party imports
from django.db import models
from django.contrib.auth.models import User
import pandas
import attrs
from rest_framework import routers, serializers, viewsets
from singleton.singleton import Singleton
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
from . import signals
from .tasks import collect_tasks, prepare_choices_tasks, ANALYSES_MODULE


# Create your models here.


class Order(models.Model):
  draft = models.BooleanField(default=False)
  complete = models.BooleanField(default=False)
  created = models.DateTimeField(verbose_name="creation datetime", auto_created=True, auto_now=True)
  # user = models.ForeignKey(User, on_delete=models.CASCADE)

  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.jobs = list()
    self.matches = list()
    self.log = logging.getLogger("orders")

  def __str__(self):
    compl = '✅️' if self.complete else '🔜️'
    d = ' DRAFT' if self.draft else ''
    creat = self.created.isoformat()
    return f"Order({creat}) {compl}{d}"

  def append(self, value):
    match value:
      case Job():
        self.jobs.append(value)
      case Match():
        self.matches.append(value)
      case _:
        raise TypeError("You cannot add object with other type than 'Match' or 'Job'.")

  def remove(self, value):
    try:
      match value:
        case Job():
          self.jobs.remove(value)
        case Match():
          self.matches.remove(value)
    except ValueError:
      self.log.warning("Try of removing item not on list."
                       "Not important, but something is bad designed.")

  def validate(self, raise_exception=False):
    if len(self.jobs) == 0 or len(self.matches) == 0:
      if raise_exception:
        raise ValueError("Order has to have at least one analysis and one match")
      return False
    return True

  def save_from_gui(self, **kwargs):
    #: before in view logic, created analyses and matches object should be added to this aggregate.
    self.validate(raise_exception=True)
    # if self.validate():
      # raise ValueError("Should be handled by showing modal to client. With info.")
    #: Actual saving
    #: First save order
    super(Order, self).save(**kwargs)
    #: Saving related objects with setting parent.
    for j in self.jobs:
      j.order = self
      j.save()
    for m in self.matches:
      m.order = self
      m.save()
    if not self.draft:
      #: send this order to receivers of new_order signal.
      #: theoretically it enough to use post_save signal, but draft will be sent then too.
      #: And this is should not be in another logic.
      signals.new_order.send(self)

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
  identifier = models.CharField(max_length=32)
  weight = models.DecimalField(max_digits=5, decimal_places=3)
  order = models.ForeignKey(Order, on_delete=models.CASCADE)


class Analysis(models.Model):
  """Managed objects by admin <-> tasks functions."""
  class Meta:
    verbose_name_plural = "analyses"
    permissions = (
      ("view", "can_view_analysis"),
      ("run", "can_run_analysis")
    )

  name = models.CharField(primary_key=True, max_length=128)
  #: Choices here are badly designed, because deploy require do migrations.
  #: TODO: Do choices dynamic, but in form probably it should be.
  task_func = models.CharField(max_length=128, choices=prepare_choices_tasks(collect_tasks()), verbose_name="Name")
  # TODO: Add this field in some next iteration
  description = models.TextField()

  def save(self, **kwargs):
    """Save Analysis with automatically setting name in it."""
    try:
      t = self.task()
      self.name = t.__analysis_name__
      #self.description = t.__doc__
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
  """Analysis in order"""
  order = models.ForeignKey(Order, on_delete=models.CASCADE)
  analysis_name = models.CharField(max_length=128, choices=prepare_choices_tasks(collect_tasks()))
  result = models.JSONField(null=True)
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


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

#: project imports
from . import signals
from .tasks import collect_tasks, prepare_choices_tasks, ANALYSES_MODULE



# Create your models here.

class Order(models.Model):
  draft = models.BooleanField(default=False)
  complete = models.BooleanField(default=False)
  # user = models.ForeignKey(django.auth.User)

  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.analyses = list()
    self.matches = list()
    self.log = logging.getLogger("orders")

  #: TODO: Validation and below method are to straight.
  def _add_or_delete_object(self, set_name_attribute, value, delete=False):
    objs_set = getattr(self, set_name_attribute)
    try:
      value.find_task()
    except AttributeError:
      pass
    except ValueError:
      self.log.warning(f"Attempt to add Analysis {value!r} with no task to invoke.")
      return
    # simple validation
    # if (not (isinstance(value, Analysis) and set_name_attribute == 'analyses')
    #     or not (isinstance(value, Match) and set_name_attribute == 'matches')):
    #   raise TypeError(f"Trying add object with wrong type '{type(value)}' to {set_name_attribute} list")
    if delete:
      try:
        objs_set.remove(value)
      except ValueError:
        self.log.warning("Try of removing item not on list. Not important, but something is bad designed.")
    else:
      if isinstance(value, list):
        objs_set.extend(value)
      else:
        objs_set.append(value)
        
  add_analysis = partialmethod(_add_or_delete_object, "analyses", delete=False)
  del_analysis = partialmethod(_add_or_delete_object, "analyses", delete=True)
  add_match = partialmethod(_add_or_delete_object, "matches", delete=False)
  del_match = partialmethod(_add_or_delete_object, "matches", delete=True)

  def save(self, **kwargs):
    if not self.draft:
      if not self.analyses:
        raise ValueError("This order has no analyses to do")
      if not self.matches:
        raise ValueError("This order has no matches!")
    #: Actual saving
    super(Order, self).save(**kwargs)
    for a in self.analyses:
      a.order = self
      a.save()
    for m in self.matches:
      m.order = self
      m.save()
    if not self.draft:
      #: send this order to receivers of new_order signal.
      signals.new_order.send(self)
  
  def is_complete(self):
    return len(self.result_set.count()) == len(self.analysis_set.count())

  def save_as_draft(self):
    self.draft = True
    self.save()

  def clone(self):
    new_order = Order(draft=True)
    new_order.matches = self.matches.copy()
    new_order.analyses = self.analyses.copy()
    return new_order


class Match(models.Model):
  identifier = models.CharField(max_length=32, primary_key=True)
  weight = models.DecimalField(max_digits=5, decimal_places=3)
  order = models.ForeignKey(Order, on_delete=models.CASCADE)


class Analysis(models.Model):
  """
      Model for managing analyses, because of they are functions,
      here is task_func_name as a choice.
      TODO: Refactoring this model, much.
  """
  # this is automatically set up from function in tasks module because of decorator there.
  name = models.CharField(primary_key=True, max_length=128)
  task_func = models.CharField(max_length=128)
  order = models.ForeignKey(Order, on_delete=models.CASCADE)
  # description = models.TextField()

  def save(self, **kwargs):
    """Save Analysis with automatically setting name to it"""
    try:
      t = self.find_task()
      self.name = t.__analysis_name__
      super().save(**kwargs)
    except:
      raise
    
  def __repr__(self):
    return f"Analysis<{self.name} --> {self.task_func}>"

  def find_task(self):
    """Returns function from python code as code. This task could be called."""
    tasks = importlib.import_module(ANALYSES_MODULE)
    if hasattr(tasks, self.task_func):
      return getattr(tasks, self.task_func)
    raise ValueError("This analysis has not implementation or name of function `task_func` is wrong.")


class Result(models.Model):
  analysis = models.OneToOneField(Analysis, on_delete=models.CASCADE)
  #: State, for now it is just JSON, features - protobuf.
  dataframe = models.JSONField()
  
  def df(self) -> pandas.DataFrame:
    return pandas.DataFrame.from_dict(jsonlib.loads(self.dataframe))
    
  def save(self, **kwargs):
    if isinstance(self.dataframe, pd.DataFrame):
      self.dataframe = self.dataframe.to_json()
    super(Result, self).save(**kwargs)
  
# TODO: add this class to stable others.
#class Description(models.Model):
  #text = models.TextField()
  #analysis = models.OneToOneField(Analysis, on_delete=models.CASCADE)
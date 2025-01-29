import importlib
import logging
from functools import partialmethod
import uuid

try:
  import orjson as jsonlib
except:
  import json as jsonlib
import pandas
from django.db import models
from rest_framework import routers, serializers, viewsets

from singleton.singleton import Singleton

from . import signals


# Create your models here.

class Order(models.Model):
  draft = models.BooleanField(default=False)
  complete = models.BooleanField(default=False)
  
  #user = models.ForeignKey(django.auth.User)
  """Property for saving order as not planned to execute analyses it have."""

  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.analyses = list()
    self.matches = list()
    self.log = logging.getLogger("orders")

  def _add_or_delete_object(self, set_name_attribute, value, delete=False):
    objs_set = getattr(self, set_name_attribute)
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
    return None
  add_analysis = partialmethod(_add_or_delete_object, "analyses", delete=False)
  del_analysis = partialmethod(_add_or_delete_object, "analyses", delete=True)
  add_match = partialmethod(_add_or_delete_object, "matches", delete=False)
  del_match = partialmethod(_add_or_delete_object, "matches", delete=True)

  def save(self):
    if not self.draft:
      if not self.analyses:
        raise ValueError("This order has no analyses to do")
      if not self.matches:
        raise ValueError("This order has no matches!")
    #: Actual saving
    super().save()
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
  name = models.CharField(max_length=128, primary_key=True)
  order = models.OneToOneField(Order, on_delete=models.CASCADE)



# For now I won't using repository, instead I will use Order.objects manager as repository.
#@Singleton
#class OrderRepository(models.Manager):
  #def __init__(self):
    #self.orders = {}

  #def add_order(self, o):
    #nid = uuid.uuid4()
    #self.orders.update(nid = o)
    #return nid

  #def remove_order(self, order_id):
    #try:
      #del self.orders[order_id]
    #except KeyError:
      #pass

  #def get_order(self, order_id) -> Order:
    #return self.orders.get(order_id, None)


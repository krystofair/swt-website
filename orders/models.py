import pandas
from django.db import models
from rest_framework import routers, serializers, viewsets
from singleton.singleton import Singleton
try:
  import orjson as jsonlib
except:
  import json as jsonlib

import importlib
import logging
from functools import partialmethod
import uuid

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

  def append(self, value):
    match value:
      case Analysis():
        self.analyses.append(value)
      case Match():
        self.matches.append(value)

  def remove(self, value):
    try:
      match value:
        case Analysis():
          try:
            self.analyses.remove(value)
        case Match():
            self.matches.remove(value)
    except ValueError:
      self.log.warning("Try of removing item not on list."
                       "Not important, but something is bad designed.")

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
      #: theoretically it enough to use post_save signal, but draft will be sent then too.
      #: And this is should not be in another logic.
      signals.new_order.send(self)

  def save_as_draft(self):
    self.draft = True
    self.save()

  def clone(self):
    new_order = Order(draft=True)
    new_order.matches = self.matches.copy()
    new_order.analyses = self.analyses.copy()
    return new_order

  def product(self):
    """Build product as website fragment. Collect results from jobs"""
    # app = pydash  # ?
    # for job in self.job_set.all():
    #   analyses.api.visual(job.name, job.df)
    #   template_view = view(job.df)


class Match(models.Model):
  identifier = models.CharField(max_length=32, primary_key=True)
  weight = models.DecimalField(max_digits=5, decimal_places=3)
  order = models.ForeignKey(Order, on_delete=models.CASCADE)


class Job(models.Model):
  name = models.CharField(max_length=128, primary_key=True)
  order = models.OneToOneField(Order, on_delete=models.CASCADE)
  result = models.JSONField(default=None)


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


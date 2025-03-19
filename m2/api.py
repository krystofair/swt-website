"""
    API for do research stuff.
"""
from django.http import Http404

import logging

from .apps import M2Config as m2_app
from . import views, services

# Create your views here.

logger = logging.getLogger(__name__)


def weight(match_id):
  """This should have a lot cache logic to not start from scratch every time."""
  return 1.0


def plan(order):
  """Plan order to processing."""
  return m2_app.engine.enqueue(order)

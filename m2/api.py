"""
    API for do research stuff.
"""
from django.http import Http404
import pandas as pd

try:
  import orjson as jsonlib
except ModuleNotFoundError:
  import json as jsonlib

from io import StringIO
import logging

from .apps import M2Config as m2_app
from . import views, services

# Create your views here.

logger = logging.getLogger(__name__)


def visualize(job, **kwargs):
  """Returns component of chart to visualize it."""
  ViewClass = views.select(job)
  try:
    if ViewClass is not None:
      if job.result is None:
        raise ValueError("Job was not processed in order.")
      result_data = jsonlib.loads(StringIO(job.result).read())
      df = pd.DataFrame.from_dict(result_data)
      logger.debug(df)
      return ViewClass.as_view(dataframe=df, **kwargs)
  except Exception as e:
    raise
  raise Http404("Not found")  # TODO: Of course here should be empty view or sth


def weight(match_id):
  """This should have a lot cache logic to not start from scratch every time."""
  return 1.0


def plan(order):
  """Plan order to processing."""
  m2_app.engine.enqueue(order)

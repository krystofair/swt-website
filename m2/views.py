"""
    API for do research stuff.
"""
from django.http import Http404, HttpResponseServerError
import pandas as pd

try:
  import orjson as jsonlib
except ModuleNotFoundError:
  import json as jsonlib

from io import StringIO

from .apps import M2Config as m2_app
from . import charts
# Create your views here.

def visualize(job, **kwargs):
  """Returns component of chart to visualize it."""
  ViewClass = charts.select(job)
  try:
    if ViewClass is not None:
      result_data = jsonlib.loads(StringIO(job.result).read())
      df = pd.DataFrame.from_dict(result_data)
      return ViewClass.as_view(dataframe=df, **kwargs)
  except:
    raise HttpResponseServerError("siup:/")
  raise Http404("Not found")  # TODO: Of course here should be empty view or sth

def weight(match_id):
  """This should have a lot cache logic to not start from scratch every time."""
  return 1.0
  
def plan(order):
  """Plan order to processing."""
  m2_app.engine.enqueue(order)

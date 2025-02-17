"""

"""
from django.views.generic import TemplateView
from django.shortcuts import render

import importlib
import copy

from . import tasks

REGISTRY = {}

def sign_for(task_func):
  def wrapper(result_class):
    # TODO: Analysis could be more than one results class.
    REGISTRY[task_func.__qualname__] = result_class
    return result_class
  return wrapper

def select(job) -> TemplateView:
  return REGISTRY.get(job.analysis().task_func, None)
  # result_class = None
  # try:
  #   this_module = importlib.import_module('charts', 'm2')
  #   result_class = getattr(this_module, REGISTRY[job.analysis().task_func])
  # except ModuleNotFoundError:
  #   # log.error("Selecting result for anlysis task {} failed.".format(
  #   #     job.analysis().task_func
  #   # ))
  #   pass
  # return result_class


class Result(TemplateView):
  template_engine = "jinja2"
  template_name = "m2/base.html"
  title = "Przegladanie wynikow"
  #:
  dataframe = None
  """
      Option JSON which describe how chart will look like.
      Read "ApexCharts" docs for constructing option.
      For basic view template `m2/analysis_result.html` is used.
  """
  def load_data(self, **kwargs):
    """Should be override for specific analysis frames."""
    raise NotImplementedError("Where is data for result?")

  def get_context_data(self, **kwargs):
    ctx = super().get_context_data(**kwargs)
    ctx.update(plots = self.load_data())
    return ctx


@sign_for(task_func=tasks.analyse_corners_line_auto)
class CornerLineAnalysisResult1(Result):
  sample_option = {
    "chart": {
      "type": 'bar'
    },
    "series": [],
    # series object is:
    # {
    #   "name": 'sales',
    #   "data": [30, 40, 35, 50, 49, 60, 70, 91, 120]
    # }
    "xaxis": {
      "categories":  [1991,1992,1993,1994,1995,1996,1997, 1998,1999]
    }
  }

  def load_data(self, **kwargs):
    option = copy.deepcopy(self.sample_option)
    df = self.dataframe
    for c in ['home', 'away']:
      option['series'].append({
        'name': c,
        'data': list(df[c])
      })
    option['xaxis']['categories'] = list(df['match_id'])
    return {"name": option, "name2": option}

"""

"""
from django.views.generic import TemplateView
from django.shortcuts import render

import importlib
import copy
import logging

from . import tasks, charts


REGISTRY = {}
logger = logging.getLogger(__name__)


def sign_for(task_func):
  def wrapper(result_class):
    # TODO: Analysis could be more than one results class.
    REGISTRY[task_func.__qualname__] = result_class
    return result_class
  return wrapper

def select(job) -> TemplateView:
  return REGISTRY.get(job.analysis().task_func, None)


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
    return {"straightforward stats": option}

@sign_for(task_func=tasks.corners_box_describe_totals)
class CornerDescribe(Result):
  def load_data(self, **kwargs):
    plot = charts.AreaChartDescribe()
    plot.add_line("total", *list(self.dataframe.loc[:,'total']))
    return {'describe corners': plot.apex()}

@sign_for(task_func=tasks.analyse_corners_2)
class CornersLinesResult2(Result):
  def load_data(self, **kwargs):
    return self.stack_bar_plot()

  def stack_bar_plot(self, **kwargs):
    plot = charts.StackBarPlot()
    plot.options.update(plot.custom_yaxis_title("weight"))
    plot.add_serie('weight_over', self.dataframe.columns,
                   list(self.dataframe.loc['weight_over', :]))
    plot.add_serie('weight_under', self.dataframe.columns,
                   list(self.dataframe.loc['weight_under', :]))
    plot.add_serie('diff_abs', self.dataframe.columns,
                   list(self.dataframe.loc['diff_abs', :]))
    return {"stackbar plot": plot.apex()}
try:
  import orjson as jsonlib
except ModuleNotFoundError:
  import json as jsonlib

import copy


class ApexChart:
  """
      Defines format for beiing interpreted by ApexCharts. JavaScript library
      for which it provides support now.
  """
  def __init__(self):
    #: For junior programmer: This is important cause options in class keep
    #: sample to use and only fill with data. And class has server process long
    #: life cycle, so it otherwise will continuously append new data.

    #: Create own instance for options from sample and get new list for series.
    self.options = copy.deepcopy(self.__class__.options)
    self.options['series'] = list()

  def apex(self):
    return self.options


class AreaChartDescribe(ApexChart):
  options = {
    "chart": {"type": "area"},
    "stroke": {"curve": "smooth"},
    "series": None,  # [{"type": "area", "data": []}
    "xaxis": {"categories": ["min", "-std", "mean", "+std", "max"]}
  }
  def add_line(self, serie_name, min, minus_std, mean, plus_std, max):
    self.options['series'].append({
      "name": serie_name,
      "data": [min, minus_std, mean, plus_std, max]
    })


class BoxPlot(ApexChart):
  options = {
    "series": None,
    "chart": {"type": "boxPlot"},
    "plotOptions": {
      "boxPlot": {
        "colors": {
          "upper": "#E61035",
          "lower": "#E6865D"
        }
      }
    }
  }
  def add_box(self, label, min, q1, q2, q3, max):
    if 'data' not in self.options['series'][0]:
      self.options['series'].append({"data": []})
    data = self.options['series'][0]['data']
    data.append({
        "x": label,
        "y": [min, q1, q2, q3, max]
    })


class StackBarPlot(ApexChart):
  options = {
    "chart": {
      "type": "bar",
      "stacked": "true"
    },
    'series': None,
    "xaxis": {
      "type": "category"
    },
    "tooltip": {
      "y": {
        "formatter": "function (val) { return val + ' units'; }"
      }
    }
  }
  def __init__(self, custom_option=None, **kwargs):
    super().__init__(**kwargs)
    if custom_option:
      self.options.update(custom_option)

  def custom_yaxis_title(self, title):
    return {
      "yaxis": {
        "title": {
          "text": title
        }
      }
    }

  def add_serie(self, serie_name, x_values, y_values):
    series = self.options['series']
    series.append({
      'name': serie_name,
      'data': [{"x": x, "y": y} for x, y in zip(x_values, y_values)]
    })
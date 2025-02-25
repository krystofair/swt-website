"""

"""
from django.views.generic import TemplateView
from django.shortcuts import render
import multidict

import importlib
import copy
import logging

from . import tasks, models


logger = logging.getLogger(__name__)


class ApexChartView(TemplateView):
  template_engine = "jinja2"
  template_name = "m2/base.html"
  title = "Przegladanie wynikow"
  order = None

  def get_context_data(self, **kwargs):
    ctx = super().get_context_data(**kwargs)
    plots, errors = models.ResultService.apexcharts_build(self.order.jobs)
    ctx.update(plots = plots, errors = errors)
    return ctx

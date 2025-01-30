from django.shortcuts import render
from django.views.generic.base import TemplateView
from django.http import JsonResponse
import orjson as jsonlib

#: API for names .
import warehouse.views as wh


class OrderCreation(TemplateView):
  template_name = "orders/create.html"
  def get_context_data(self, **kwargs):
      context = super().get_context_data(**kwargs)
      context["countries"] = wh.Names.list_countries()
      lbc = dict()
      for c in context['countries']:
        lbc.update({c: wh.Names.list_leagues(c)})
      context['leagues_by_countries'] = str(lbc)
      return context


def leagues(request, country, **kwargs):
  ls = wh.Names.list_leagues(country.lower())
  return JsonResponse(ls, safe=False)
from django.forms import ModelChoiceField
from django.forms.models import ModelChoiceIterator
from django.shortcuts import render, reverse, loader
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.views.generic.base import TemplateView
from django.http import JsonResponse, HttpResponseRedirect, HttpResponse, HttpRequest
from django import forms
import orjson as jsonlib

#: API for names .
import warehouse.views as wh
from kasbeer.forms import MatchInlineEntryForm, FilteringForm, MatchFormSet

class OrderCreation(TemplateView):
  template_name = "kasbeer/new-order-view.html"
  template_engine = 'jinja2'
  title = "Order Creation"
  # form = FilteringForm()

  def get_context_data(self, **kwargs):
    context = super().get_context_data(**kwargs)
    context["countries"] = wh.Names.list_countries()
    lbc = dict()
    for c in context['countries']:
      lbc.update({c: wh.Names.list_leagues(c)})
    context['leagues_by_countries'] = str(lbc)
    return context

  def get(self, request, *args, **kwargs):
    return super().get(request, *args, **kwargs)

  def post(self, request, *args, **kwargs):
    form = FilteringForm(request.POST)
    return super().get(request, *args, **kwargs)

# @method_decorator(never_cache, name='dispatch')
class TestingForms(TemplateView):
  template_engine = 'jinja2'
  title = "Tworzenie orderu :O"
  template_name = "kasbeer/new-order-view.html"

  def _prepare_url_(self, tn):
    tn = tn.rstrip('.html')
    self.template_name = f"/kasbeer/{tn}.html"

  def get_context_data(self, **kwargs):
    return super().get_context_data(**kwargs)

  def get(self, request, *args, **kwargs):
    ctx = {}
    if request.GET.dict():
      form = FilteringForm(request, request.GET)
    else:
      form = FilteringForm(request)
    ctx['form'] = form
    if form.is_valid():
      #: Find all matches from filters - call API
      matches = form.search()
      mform = MatchFormSet(games=matches)
      ctx |= {'matches': mform}
    ctx |= self.get_context_data(**ctx)
    resp = render(request, template_name=self.template_name,
                  using=self.template_engine, context=ctx)
    return resp

def leagues(request, country, **kwargs):
  ls = wh.Names.list_leagues(country.lower())
  return JsonResponse(ls, safe=False)
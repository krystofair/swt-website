# django imports
from django.forms import ModelChoiceField
from django.forms.models import ModelChoiceIterator
from django.shortcuts import render, reverse, loader, redirect
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.views.generic.base import TemplateView, View
from django.http import JsonResponse, HttpResponseRedirect, HttpResponse, HttpRequest
from django import forms

# other third-party
import orjson as jsonlib

# built-ins
import logging

# project's imports
#: API for names .
import warehouse.views as wh
from kasbeer.forms import MatchInlineEntryForm, FilteringForm, MatchFormSet
from kasbeer import models
from m2.views import visualize


logger = logging.getLogger(__name__)


def order_result_view(request, order_id, *args, **kwargs) -> View:
  order = models.Order.objects.get(id=order_id)
  job = order.jobs[0]
  view = visualize(job, **kwargs)
  return view(request)


class OrderCreation(TemplateView):
  template_name = "kasbeer/new-order-view.html"
  template_engine = 'jinja2'
  title = "Tworzenie zamówienia"
  _orders = dict()
  # form = FilteringForm()

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

  def post(self, request, action, *args, **kwargs):
    ctx = {}
    try:
      match action:
        case 'games': ctx |= self._add_matches_action(request)
        case 'accept': ctx |= self._commit_order_action(request)
      ctx |= super().get_context_data()
      ctx.update(form=FilteringForm(request))
      return render(request, template_name=self.template_name,
                    using=self.template_engine, context=ctx)
    except ValueError as e:
      logger.exception(e)
      return HttpResponse(b"Przetwarzanie zlecenia sie nie powiodlo przykro mi")

  def get_order_by_session(self, request):
    try:
      order = self._orders[request.session.session_key]
    except KeyError:  # order jeszcze nie istnieje
      order = models.Order(draft=False)
    self._orders[request.session.session_key] = order
    return self._orders[request.session.session_key]

  def _add_matches_action(self, request, **kwargs):
    #: Pobierz mecze z formularza po zatwierdzeniu
    order = self.get_order_by_session(request)
    formset = MatchFormSet(request.POST)
    if formset.is_valid():
      for match_form in formset:
        m = match_form.cleaned_data['match']
        order.append(m)
        logger.info(f"add match {m!r} to order")
      kwargs.update(matches=formset)
    return kwargs

  def _commit_order_action(self, request, **kwargs):
    order = self.get_order_by_session(request)
    job = models.Job(analysis_name="Analiza rzutów rożnych 1")
    order.append(job)
    #: This try is for saving order as draft if something goes wrong
    #: Then raise (not yet defined) exception to inform user.
    # try:
    order.user = request.user
    order.save()
    logger.info(f"Order created at {order.created_at} for user {request.user}")
    del self._orders[request.session.session_key]
    # except ValueError as e:
    #   try:
    #     order.save_as_draft()
    #     del self._orders[request.session.session_key]
    #     raise
    #   except:
    #     raise e from None
    return kwargs


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
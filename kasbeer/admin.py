from django.contrib import admin
from django import forms
from guardian import admin as guardAdmin

import logging

from .models import Analysis, Order, Match, Job
import warehouse.views as wh

# Register your models here.


class JobInline(admin.TabularInline):
  model = Job
  fields = ['analysis_name']
  exclude = ['result']
  extra = 1

class MatchInlineForm(forms.BaseInlineFormSet):
  # summary = forms.CharField(widget=forms.Textarea)
  # weight = forms.DecimalField(widget=forms.Rang)
  pass

class MatchInline(admin.TabularInline):
  model = Match
  verbose_name_plural = "matches"
  extra = 0
  can_delete = False

  def has_add_permission(self, request, obj):
    return False

  def has_delete_permission(self, request, obj=None):
    return False

  def has_change_permission(self, request, obj=None):
    return False

  # XXX: There is possible to exclude editable too, by permissions.
  # XXX: Maybe it's not possible, but there is a class which checks permission of it.

@admin.register(Analysis)
class AnalysisAdmin(guardAdmin.GuardedModelAdmin):
  exclude = ['name']
  search_fields = ['name', 'description']


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
  list_display = [ 'created_at', 'user', 'complete', 'draft', 'id',]
  inlines = [JobInline, MatchInline]
  list_filter = ['user', 'created_at', 'complete']

  def save_model(self, request, obj, form, change):
    """
        Arguments:
          change: means that this is not new instance of Order.
          obj: is an instance of Order
          form: is whole form with inline jobs and matches.
          request: can check permissions, access to POST params etc.
    """
    # JobFactory = forms.inlineformset_factory(Order, Job, exclude=JobInline.exclude)
    # try:
    #   MatchFactory = forms.inlineformset_factory(Order, Match, fields=MatchInline.fields)
    # except Exception as e:
    #   logging.getLogger(__name__).warning(e)
    # jf = JobFactory()
    # import pdb; pdb.set_trace()
    # obj.validate(raise_exception=True)
    super().save_model(request, obj, form, change)

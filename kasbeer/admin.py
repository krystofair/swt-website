from django.contrib import admin
from django import forms
from guardian import admin as guardAdmin


from .models import Analysis, Order, Match, Job
import warehouse.views as wh

# Register your models here.


class JobInline(admin.TabularInline):
  model = Job
  exclude = ['result']
  extra = 0


class MatchInline(admin.TabularInline):
  model = Match
  verbose_name_plural = "matches"
  extra = 0
  can_delete = False
  # XXX: There is possible to exclude editable too, by permissions.
  # XXX: Maybe it's not possible, but there is a class which checks permission of it.

@admin.register(Analysis)
class AnalysisAdmin(guardAdmin.GuardedModelAdmin):
  exclude = ['name']
  search_fields = ['name', 'description']


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
  list_display = ['id', 'created',  'complete', 'draft']
  inlines = [JobInline, MatchInline]

  def save_model(self, request, obj, form, change):
    # TODO: place when we see inlines saved with model. Here we should add inlines to obj in order to save them with it
    # or remove them.
    super().save_model(request, obj, form, change)

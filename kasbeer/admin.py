from django.contrib import admin
from guardian import admin as guardAdmin

from .models import Analysis, Order

# Register your models here.

@admin.register(Analysis)
class AnalysisAdmin(guardAdmin.GuardedModelAdmin):
  exclude = ['name']
  


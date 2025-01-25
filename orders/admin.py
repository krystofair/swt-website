from django.contrib import admin
from . import models

# Register your models here.

admin.register(models.Order, models.Analysis, models.Match)

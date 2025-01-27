from django.contrib import admin
from . import models

# Register your models here.

# No tak tutaj można zdefiniować modele analiz w celach ograniczania dostępu konkretnym użytkownikom.

admin.register(models.Analysis)
from django.apps import AppConfig
from django.core import signals


class OrdersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'orders'
    
    def ready(self):
        from . import models
        from analyses import signals as asigs
        asigs.analysis_complete.connect(models.Result.save_result)
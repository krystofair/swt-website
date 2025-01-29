from django.apps import AppConfig

import aleksander
from aleksander import dblayer
import sqlalchemy as sa


class WarehouseConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'warehouse'
    def ready(self):
        # create data db manager with connection pool  # this will be added in aleksander==1.2.0
        #: add additional kwargs when creating engine if aleksander module is in 1.2.0 version.
        pool_kwargs = dict(pool_size=10, max_overflow=0)
        pool_kwargs = pool_kwargs if aleksander.__version__ == "1.2.0" else dict()
        self.dbmgr = dblayer.DbMgr('sqlite', **pool_kwargs)
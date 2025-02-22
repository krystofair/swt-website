import pandas
try:
  import orjson as jsonlib
except ModuleNotFoundError:
  import json as jsonlib

import os
import queue
import threading
import multiprocessing as mp
import logging

from kasbeer import models

import psycopg2 as pg
PG_DB_ERRORS = (pg.DatabaseError, pg.InterfaceError, pg.OperationalError)


class Engine():
  """Engine to manage processing orders."""
  QUEUE_TIMEOUT_SECS = 10800  # 3h
  _instance = None

  def __new__(cls, *args, **kwargs):
    """ For being singleton"""
    if cls._instance:
      return cls._instance
    return super().__new__(cls, *args, **kwargs)
    
  def __init__(self, **kwargs):
    cls = self.__class__
    if cls._instance:
      return
    self.queue = mp.Queue()
    self.log = logging.getLogger("m2.Engine")
    self.log.debug("Initialization Engine")
    self.proc_kwargs = kwargs
    self.process = Process(self.queue, **self.proc_kwargs)
    cls._instance = self
      
    # self.manager = mp.Manager()  # returns STARTED SyncManager
    # log.info("Started SyncManager at address {}".format(self.manager.address))
    #: With first order enqueue spawn new process.
  @property
  def instance(self):
    return self.__class__._instance

  def start(self):
    self = self.instance  # this should be override in __get_attribute__ in this very class.
    if self.process:
      self.process.start()
      self.log.info("Engine process spawn with PID {}".format(self.process.pid))
    else:
      self.log.error("There is no process created to run.")
    
  
  def enqueue(self, order):
    """Put order to queue for future processing."""
    self = self.instance
    try:
      #: Don't process drafts.
      if order and order.draft:
        return
      self._health_check_process()
      self.queue.put(order.id)
      self.log.info("New order(its id) on queue: {order}".format(order=order))
    except KeyError:
      # never raised.
      self.log.error(f"Did not enqueue order, because there is no order. Receive those: {kwargs=}")
  
  def _health_check_process(self):
    self = self.instance
    if not self.process or not self.process.is_alive():
      self.log.warning("Process is not alive. Start new one. CHECK OUT LOGS OF PROCESS.")
      self.start()

class Process(mp.Process):
  """
      Engine process to do "black" job.
  """
  PROCESS_LOG_FILE = "./m2engine.log"

  def __init__(self, queue, pool_size=1, **kwargs):
    daemon = kwargs.pop('daemon', True)
    super().__init__(daemon=daemon, **kwargs)
    self.queue = queue
    # self.pool = mp.pool.Pool(pool_size)
    self.logger = logging.getLogger("m2.svc.EngineExecutor")
    self.logger.addHandler(logging.FileHandler(self.PROCESS_LOG_FILE))
    self._stopped = False
    
  def terminate(self):
    self._stopped = True
    self.queue.put(None)  # to unchoke queue.get without waiting timeout.

  def run(self):
    #: Some initialization to not getting stupid warnings
    import sys
    #: Closing std output
    sys.stdout.close()
    sys.stdout = open(os.open(os.devnull, os.O_WRONLY), closefd=False)
    sys.stderr.close()
    sys.stderr = open(os.open(os.devnull, os.O_WRONLY), closefd=False)
    #: Run processing orders
    self._processing_orders()
    
  def _processing_orders(self):
    from django import db
    self.logger.info("Start processing orders.")
    while not self._stopped:
      try:
        order_id = self.queue.get(timeout=Engine.QUEUE_TIMEOUT_SECS)
        order = models.Order.objects.get(id=order_id) if order_id else None
        self.process_order(order)
      except PG_DB_ERRORS as exc:
        self.logger.error(exc)
        self.logger.info("Closing old connections")
        db.close_old_connections()
      except queue.Empty:
        #: Close old connection after timeout occured.
        #  Timeout should be synchronized with CON_MAX_AGE ;)
        db.close_old_connections()
      # TODO: except OrderProcessingError:  # or sth like that.
      except Exception as e:
          self.logger.exception(e)
        

  def process_order(self, order):
    """
        Process single order, which was received from queue.
        So many questions here, is it possible to save job like normal in django in another process?
        TODO: Change it. - now here pool is not used.
    """
    if order is None:
      self.logger.info("None as order - processing order stops here.")
      return
    log = self.logger
    # order = models.Order.objects.get(id = order_id)
    #: Order which all jobs succeed are treat as failure to watch by admin or someone in charge.
    results = 0
    log.debug("Processing order! {!r}".format(order))
    jobs = order.job_set.all()
    log.debug(f"All jobs for that order: {jobs=!r}")
    for job in jobs:
      #: search reference analysis by name
      analysis = job.analysis()
      log.debug(f"Found analysis! {analysis=!r}")
      try:
        log.debug(models.Analysis.objects.all())
        #: WARNING! If this can be run by specific user? Where the user object coming from?  - from order see orders.models
        task = analysis.task()
        #task.delay() # XXX: this will be in power when use celery.
        try:
          dataframe = task(list(order.match_set.all()))
          job.error = None  # important when calculated second time
          results += 1
        except Exception as e:
          job.error = str(e)[:256]
          dataframe = pandas.DataFrame()
        job.df = dataframe
        log.debug(job.df)
        job.save()
      except models.Analysis.DoesNotExist:
        log.warning("User choose analysis which wasn't add by admin.")
      except Exception as e:
        log.exception(e)
        # TODO: notify Admin,
        r = jsonlib.dumps(dict(error=str(e)))
        log.error(r)
    order.set_complete()
    log.info("Processing order ends. {}".format(order))

# def process_order(order):
#   """
#       Process single order, which was received from queue.
#       So many questions here, is it possible to save job like normal in django in another process?
#   """
#   #: Order which all jobs succeed are treat as failure to watch by admin or someone in charge.
#   results = 0
#   log.debug(f"{args=}, {kwargs=}")
#   log.debug("Processing order! {!r}".format(order))
#   jobs = order.job_set.all()
#   log.debug(f"All jobs for that order: {jobs=!r}")
#   for job in jobs:
#     #: search reference analysis by name
#     analysis = job.analysis()
#     log.debug(f"Found analysis! {analysis=!r}")
#     try:
#       log.debug(models.Analysis.objects.all())
#       #: WARNING! If this can be run by specific user? Where the user object coming from?  - from order see orders.models
#       task = analysis.task()
#       #task.delay() # XXX: this will be in power when use celery.
#       try:
#         dataframe = task(list(order.match_set.all()))
#         job.error = None  # important when calculated second time
#         results += 1
#       except Exception as e:
#         job.error = str(e)[:256]
#         dataframe = pandas.DataFrame()
#       job.df = dataframe
#       log.debug(job.df)
#       job.save()
#     except models.Analysis.DoesNotExist:
#       log.warning("User choose analysis which wasn't add by admin.")
#     except Exception as e:
#       log.exception(e)
#       # TODO: notify Admin,
#       r = jsonlib.dumps(dict(error=str(e)))
#       log.error(r)
#   order.set_complete()
#   log.info("Processing order ends. {}".format(order))

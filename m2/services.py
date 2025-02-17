from django.dispatch import receiver
import pandas
try:
  import orjson as jsonlib
except ModuleNotFoundError:
  import json as jsonlib

import os
import queue
import threading
import logging

from kasbeer import models
from tutu.settings import ANALYSIS_SINK_PATH


class Engine:
  """Orders Processing Service"""
  def __init__(self):
    self.orders_que = queue.Queue()
    self.log = logging.getLogger(f"{self.__module__}.{self.__class__.__name__}")
    self._ord_processing_thread_ref = None

  def enqueue(self, order):
    """Function to enqueuing orders, used by signal dispatcher where new_order was created_at."""
    try:
      #: Don't process drafts.
      if order.draft:
        return
      self.orders_que.put(order)
      self.log.info("New order on queue: {order}".format(order=order))
      if not self._ord_processing_thread_ref or not self._ord_processing_thread_ref.is_alive():
        self._ord_processing_thread_ref = threading.Thread(target=self.__orders_processing(), daemon=True)
        self._ord_processing_thread_ref.start()
        self.log.info("Thread of processing orders started")
    except KeyError:
      # never raised.
      self.log.error(f"Did not enqueue order, because there is no order. Receive those: {kwargs=}")

  def __orders_processing(self):
    """Processing orders one by one, by single thread until queue will be empty."""
    TIMEOUT = 120.0  # in seconds
    self.log.debug("orders processing started")
    try:
      while not self.orders_que.empty():
        thread = threading.Thread(target=self.__process_order)
        thread.start()
        self.log.debug("Next order start processing.")
        thread.join(timeout=TIMEOUT)  # two minute is enough for single order?
        # PROPOSAL: maybe wait some time for probability of taken new order in this time,
        #           so this wont quit from this thread.
    except TimeoutError:
      self.log.error(f"Processing order {self.order!r} last over {TIMEOUT}s.")
    self.log.debug("orders processing ended")

  def __process_order(self):
    results = 0
    #: get order from queue
    order = self.orders_que.get()
    self.log.debug("Processing order! {!r}".format(order))
    jobs = order.job_set.all()
    self.log.debug(f"All jobs for that order: {jobs=!r}")
    for job in jobs:
      #: search reference analysis by name
      analysis = job.analysis()
      self.log.debug(f"Found analysis! {analysis=!r}")
      try:
        self.log.debug(models.Analysis.objects.all())
        #: WARNING! If this can be run by specific user? Where the user object coming from?  - from order see orders.models
        task = analysis.task()
        #task.delay() # XXX: this will be in power when use celery.
        try:
          dataframe = task(list(order.match_set.all()))
        except Exception as e:
          job.error = str(e)[:256]
          dataframe = pandas.DataFrame()
        results += 1
        job.df = dataframe
        self.log.debug(job.df)
        job.save()
      except models.Analysis.DoesNotExist:
        self.log.warning("User choose analysis which wasn't add by admin.")
      except Exception as e:
        self.log.exception(e)
        # TODO: notify Admin.
        r = jsonlib.dumps(dict(error=str(e)))
    order.set_complete()
    self.log.info("Processing order completed. {}".format(order))

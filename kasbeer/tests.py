from django.test import TestCase

from time import sleep
import logging

from .services import Engine
from . import models, signals, tasks

# Create your tests here.


#class AnalysisModelAndTask(TestCase):
  #def test_searching_analysis_by_name(self):
    #o = models.Order()
    #with TestCase.assertRaises(ValueError):
      #o.save()
    #a = models.Analysis(order=models.Order)
    #a.task_func = "analyse_corners_line_auto"
    #o.add_analysis(a)
    #o.save()
    #a2 = models.Analysis.objects.get(name=a.name)
    #assert a2 == a
    #assert a2.task_func == 'analyse_corners_line_auto'
    #assert a2.name == 'Analiza rzutów rożnych 1'
    #task = a2.find_task()
    #assert task.__qualname__ == 'analyse_corners_line_auto'
    #assert task.__analysis_name__ == 'Analiza rzutów rożnych 1'

  #def test_calculating_task(self):
    #a = models.Analysis()
    #a.task_func = "test_task"
    #a.save()
    #task = a.find_task()
    #result = task([1,2,3,4])
    #assert result.loc[0,'c'] == 3
    #assert result.iloc[1, 1] == 2


#class TestEngine(TestCase):

  #@classmethod
  #def setUpClass(cls):
    ##: prepare analysis added by admin.
    #a = models.Analysis()
    #a.task_func = "test_task"
    #a.save()

  #def test_process_order(self):

    #a = models.Analysis.objects.get(task_func = 'test_task')
    ##: Prepare order
    #o = models.Order(draft=False)
    ## oa = models.Analysis(name='Testowa analiza - nie robi nic i nie spełnia sygnatury analizy', order=o)
    #oa = models.Analysis(name=a.name, order=o)
    #om = models.Match(identifier='123', weight=1.3, order=o)
    #o.add_analysis(oa)
    #o.add_match(om)
    ##: Dont save it yet, cause it sends signal
    ## o.save()
    ##: create engine.
    #engine = Engine()
    #signals.new_order.connect(engine.enqueue)
    ##: connect analyses signal, that's how it is doing in orders to save result there
    ##signals.analysis_complete.connect(models.Result.save_result)
    ##: save order to send signal
    #o.save()
    ##: After that oa should have result
    #sleep(0.100)  # let's wait 100ms. to be sure that thread do his job.
    #assert oa.result_set.first() == models.Result.objects.get(analysis = oa)



class TcOrder(TestCase):
  def setUp(self):
    self.analyses = [ { "name":"Testowa analiza - nie robi nic i nie spełnia sygnatury analizy" }, { "name":"Analiza rzutów rożnych 1"}]
    self.matches = [ { "identifier":"1", "weight":0.4 },
                { "identifier":"2", "weight":1.2 },
                { "identifier":"3", "weight":-0.3 }
              ]
    self.log = logging.getLogger("TcOrder_TestCase")
    
  def test_create_new_order(self):
    
    def build_obj_analyses():
      obj_analyses = list()
      for a in self.analyses:
        n = a['name']
        my_tasks = tasks.collect_tasks()
        for t in my_tasks:
          if t['name'] == n:
            an = models.Analysis(name = n, task_func = t['task_func'])
            obj_analyses.append(an)
      return obj_analyses
    
    #: create order object per session
    order = models.Order(draft=False)
    #: Order not draft cannot be saved without matches or analyses.
    with self.assertRaises(ValueError):
      order.save()
    #: Prepare analyses and matches mocks, with assigned order
    
    obj_analyses = build_obj_analyses()
    obj_matches = [models.Match(**m, order=order) for m in self.matches]
    #: Add matches and analyses to order, cause it is not propagated with assigning.
    for m in obj_matches:
      order.add_match(m)
    for a in obj_analyses:
      order.add_analysis(a)
    #: Saving order in good state.
    order.save()
    #: Checks
    orders = models.Order.objects.all()
    assert len(orders) == 1
    o = orders[0]
    try: obj_analyses.index(o.analysis_set.filter(name="Analiza rzutów rożnych 1").get())
    except: assert False, "There should be this analysis, probably at last position"
    else: assert True
    
  #def test_saving_order_as_a_whole_not_alone_parts(self):
    #order = models.Order()
    #obj_analyses = [models.Analysis(**a) for a in self.analyses]
    #obj_matches = [models.Match(**m) for m in self.matches]
    #for m in obj_matches:
      #order.add_match(m)
    #assert order.matches == obj_matches
    #for a in obj_analyses:
      #order.add_analysis(a)
    #order.save()
    #o = list(models.Order.objects.all())[0]
    #assert list(o.match_set.all()) == obj_matches, (o.match_set.all(), obj_matches)
    #assert list(o.analysis_set.all()) == obj_analyses, (o.analysis_set.all(), obj_analyses)
    ##: Test if after delete o there is no more elements,
    ## this tests are stupid cause single test case is atomic.
    #Order.objects.delete(o)
    #assert list(models.Analysis.objects.all()) == []
    #assert list(models.Match.objects.all()) == []

  def test_cloning_order(self):
    # create order for base
    order = models.Order(draft=True)
    order.save()
    [order.add_analysis(models.Analysis(**a, order=order)) for a in self.analyses]
    [order.add_match(models.Match(**m, order=order)) for m in self.matches]
    # clone order
    order2 = order.clone()
    # checks - should have the same matches and analyses
    # 1. matches always can be deleted or theirs weights changes.
    assert order2.analyses == order.analyses
    assert order2.matches == order.matches


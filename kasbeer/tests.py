from django.test import TestCase

from . import models, services, signals

class Testing(TestCase):
  def setUp(self):
    pass
  
  def test_analysis(self):
    #: add analysis:
    #: have to be function from tasks otherwise failed.
    analysis = models.Analysis(task_func = "test_task")
    analysis.save()
    self.assertEqual(analysis.name, "Testowa analiza")
    #: raise when uknown task, this cannot be created, because of choices in task_func field.
    with self.assertRaises(ValueError):
      wrong_analysis = models.Analysis(task_func = "unknown task")
      wrong_analysis.save()
  
  def test_process_order_creation(self):
    order = models.Order()  # creating order as normal (no draft)
    self.assertFalse(order.complete)
    #: Cannot save in this state.
    with self.assertRaises(ValueError):
      order.save()
      
    #: Cannot append random object to order.
    with self.assertRaises(TypeError):
      order.append("sigma")
      
    #: Can be only models.Match and models.Analysis
    analysis = models.Analysis(task_func = 'test_task')
    job = models.Job(analysis_name=analysis.name)
    order.append(job)
    match = models.Match(identifier = '123', weight=1.0)
    order.append(match)
    order.save()
    return order
    
  def test_processing_order(self):
    self.skipTest("Cause transactions sucks in tests and additionally threads or etc. I will never test this out lol")
    #: get new order
    order = self.test_process_order_creation()
    #: create engine to processing orders
    engine = services.Engine()
    
    # TODO: Signals have to be done later.
    #: connect engine to signal
    #signals.new_order.connect(engine.enqueue)
    #: send signal - start engine
    #signals.new_order.send(order)
    self.assertEqual(order.job_set.count(), 1)
    engine.enqueue(order)
    from time import sleep
    sleep(1) # wait a second
    #: Check results
    
    self.assertTrue(order.complete)
    r = list(order.job_set.all())[0]
    df = r.dataframe()
    self.assertEqual(df.iloc[0,1], 2)
    self.assertEqual(df.loc[1, 'c'], 7)      


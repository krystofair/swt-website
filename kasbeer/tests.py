from django.test import TestCase

from . import models
from .models import Order, Analysis, Match


# Create your tests here.

class TcOrder(TestCase):
  def setUp(self):
    self.analyses = [{"name": "A"}, {"name": "B"}, {"name": "C"}]
    self.matches = [{"identifier": "1", "weight": 0.4},
                    {"identifier": "2", "weight": 1.2},
                    {"identifier": "3", "weight": -0.3}
                    ]

  def test_create_new_order(self):
    #: create order object per session
    order = Order(draft=False)
    #: Order not draft cannot be saved without matches or analyses.
    with self.assertRaises(ValueError):
      order.save()
    #: Prepare analyses and matches mocks, with assigned order
    obj_analyses = [Analysis(**a, order=order) for a in self.analyses]
    obj_matches = [Match(**m, order=order) for m in self.matches]
    #: Add matches and analyses to order, cause it is not propagated with assigning.
    for m in obj_matches:
      order.add_match(m)
    for a in obj_analyses:
      order.add_analysis(a)
    #: Saving order in good state.
    order.save()
    #: Checks
    orders = Order.objects.all()
    assert len(orders) == 1
    o = orders[0]
    try:
      obj_analyses.index(o.analysis_set.filter(name="A").get())
    except:
      assert False, "There should be this analysis, probably at last position"
    else:
      assert True



class Testing(TestCase):
  def setUp(self):
    self.user = models.User.objects.get(pk=1)  # AnonymousUser
    pass
  
  def test_analysis(self):
    #: add analysis:
    #: have to be function from tasks otherwise failed.
    analysis = models.Analysis(task_func = "test_task")
    analysis.save()
    self.assertEqual(analysis.name, "Testowa analiza")
    #: raise when uknown task, this cannot be created_at, because of choices in task_func field.
    with self.assertRaises(ValueError):
      wrong_analysis = models.Analysis(task_func = "unknown task")
      wrong_analysis.save()
  
  def test_process_order_creation(self):
    order = models.Order(user=self.user)  # creating order as normal (no draft)
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
    self.skipTest("Rewrite it in new matter.")

  def test_cloning_order(self):
    """Skip now but add it here from old app to remember about this feature"""
    # create order for base
    self.skipTest("feature not implemented yet")
    order = Order(draft=True)
    order.save()
    [order.add_analysis(Analysis(**a, order=order)) for a in self.analyses]
    [order.add_match(Match(**m, order=order)) for m in self.matches]
    # clone order
    order2 = order.clone()
    # checks - should have the same matches and analyses
    # 1. matches always can be deleted or theirs weights changes.
    assert order2.analyses == order.analyses
    assert order2.matches == order.matches

class Forms(TestCase):
  def test_analyses_choices_form(self):
    from kasbeer import forms
    form = forms.AnalysesForm()

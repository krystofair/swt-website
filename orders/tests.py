from django.test import TestCase

from .models import Order, Analysis, Match

# Create your tests here.

class TcOrder(TestCase):
  def setUp(self):
    self.analyses = [ { "name":"A" }, { "name":"B"}, { "name":"C"} ]
    self.matches = [ { "identifier":"1", "weight":0.4 },
                { "identifier":"2", "weight":1.2 },
                { "identifier":"3", "weight":-0.3 }
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
    try: obj_analyses.index(o.analysis_set.filter(name="A").get())
    except: assert False, "There should be this analysis, probably at last position"
    else: assert True
    
  def test_saving_order_as_a_whole_not_alone_parts(self):
    order = Order()
    obj_analyses = [Analysis(**a) for a in self.analyses]
    obj_matches = [Match(**m) for m in self.matches]
    for m in obj_matches:
      order.add_match(m)
    assert order.matches == obj_matches
    for a in obj_analyses:
      order.add_analysis(a)
    order.save()
    o = list(Order.objects.all())[0]
    assert list(o.match_set.all()) == obj_matches, (o.match_set.all(), obj_matches)
    assert list(o.analysis_set.all()) == obj_analyses, (o.analysis_set.all(), obj_analyses)
    #: Test if after delete o there is no more elements,
    # this tests are stupid cause single test case is atomic.
    Order.objects.delete(o)
    assert list(Analysis.objects.all()) == []
    assert list(Match.objects.all()) == []

  def test_cloning_order(self):
    # create order for base
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
    
  def test_analysis_done():
    import pandas as pd
    o = Order()
    a = Analysis(name='aliza', order=Order())
    a.result.dataframe = pd.DataFrame()
    

  

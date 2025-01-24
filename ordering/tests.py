from django.test import TestCase

from .models import Order, Analysis, Match

# Create your tests here.

class TcOrder(TestCase):
  def setUp(self):
    true, false = True, False
    self.analyses = [ { "name":"A", "done":false }, { "name":"B", "done":true }, { "name":"C", "done":true } ]
    self.matches = [ { "identifier":"1", "weight":0.4 },
                { "identifier":"2", "weight":1.2 },
                { "identifier":"3", "weight":-0.3 }
              ]   
    
  def test_order(self):
    order = Order(draft=False)
    # order.save()  # cannot be saved because of no analyses added yet.
    obj_analyses = [Analysis(**a, order=order) for a in self.analyses]
    obj_matches = [Match(**m, order=order) for m in self.matches]
    #: Bad solution - saving single matches and analyses not from order context
    try:
      for m in obj_matches:
        m.save()
      for a in obj_analyses:
        a.save()
    except ValueError:
      assert True
    else:
      assert False, "Saving matches or analysis as single instances is denied."
    #: #####
    #: Good solution - saving matches and analyses where order's save methods is invoked.
    for m in obj_matches:
      order.add_match(m)
    for a in obj_analyses:
      order.add_analysis(a)
    order.save()
    #:#####
    orders = Order.objects.all()
    assert len(orders) == 1
    o = orders[0]
    try: obj_analyses.index(o.analysis_set.filter(name="A").get())
    except: assert False, "There should be this analysis, probably at last position"
    else: assert True
    #: This is important to remember, we saved analyses for order after saving order this
    o.analyses.clear()  # clear analyses list, this action will never happen, cause we don't manipulate it from python internals
    o.draft = True
    o.save()
    
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
    
  def test_cloning_order(self):
    order = Order(draft=True)
    order.save()
    [order.add_analysis(Analysis(**a, order=order)) for a in self.analyses]
    [order.add_match(Match(**m, order=order)) for m in self.matches]
    order2 = order.clone()
    assert order2.analyses == order.analyses
    assert order2.matches == order.matches
    

  
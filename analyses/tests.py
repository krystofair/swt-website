from django.test import TestCase

from time import sleep

from orders import models as ord_models
from orders import signals as ord_signals
from .services import Engine
from . import models
from . import signals as ana_signals

# Create your tests here.


class AnalysisModelAndTask(TestCase):
    def test_searching_analysis_by_name(self):
        a = models.Analysis()
        a.task_func = "analyse_corners_line_auto"
        a.save()
        a2 = models.Analysis.objects.get(name=a.name)
        assert a2 == a
        assert a2.task_func == 'analyse_corners_line_auto'
        assert a2.name == 'Analiza rzutów rożnych 1'
        task = a2.find_task()
        assert task.__qualname__ == 'analyse_corners_line_auto'
        assert task.__analysis_name__ == 'Analiza rzutów rożnych 1'

    def test_calculating_task(self):
        a = models.Analysis()
        a.task_func = "test_task"
        a.save()
        task = a.find_task()
        result = task([1,2,3,4])
        assert result.loc[0,'c'] == 3
        assert result.iloc[1, 1] == 2

class TestEngine(TestCase):

    @classmethod
    def setUpClass(cls):
        #: prepare analysis added by admin.
        a = models.Analysis()
        a.task_func = "test_task"
        a.save()

    def test_process_order(self):
        
        a = models.Analysis.objects.get(task_func = 'test_task')
        #: Prepare order
        o = ord_models.Order(draft=False)
        # oa = ord_models.Analysis(name='Testowa analiza - nie robi nic i nie spełnia sygnatury analizy', order=o)
        oa = ord_models.Analysis(name=a.name, order=o)
        om = ord_models.Match(identifier='123', weight=1.3, order=o)
        o.add_analysis(oa)
        o.add_match(om)
        #: Dont save it yet, cause it sends signal
        # o.save()
        #: create engine.
        engine = Engine()
        ord_signals.new_order.connect(engine.enqueue)
        #: connect analyses signal, that's how it is doing in orders to save result there
        ana_signals.analysis_complete.connect(ord_models.Result.save_result)
        #: save order to send signal
        o.save()
        #: After that oa should have result
        sleep(0.100)  # let's wait 100ms. to be sure that thread do his job.
        assert oa.result_set.first() == ord_models.Result.objects.get(analysis = oa)
        
        



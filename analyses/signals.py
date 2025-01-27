from django.core import signals

#: Sends analysis of order and result as json string.
analysis_complete = signals.Signal()  #receiver(sender, kwargs={order_analysis, result})
order_complete = signals.Signal()  #receiver(sender, kwargs={order})
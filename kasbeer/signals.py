from django.core import signals

#: Sending from Order model's .save() method when order is not draft and should be start to processing.
new_order = signals.Signal()  # receiver(order, **kwargs) = post_save of order model

#: Sends analysis of order
analysis_complete = signals.Signal()  # receiver(analysis, **kwargs)
order_complete = signals.Signal()  # receiver(order, **kwargs)
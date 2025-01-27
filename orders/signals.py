from django.core import signals

#: Sending from Order model's .save() method when order is not draft and should be start to processing.
new_order = signals.Signal()
from django import forms
from django.forms import HiddenInput, Select
from django.utils import choices

import functools

from .models import Match
import warehouse.views as wh
from .filtering import FilteringForm


class MatchSpecializedForm(forms.Form):
  # template_engine = 'jinja2'
  # class Meta:
  #   model = Match
  #   fields = ['checked', 'summary', 'weight', 'identifier']
    # exclude = ['identifier']
  __name__ = "MatchSpecializedForm"  # setting it is a hit.
  template_name_div = "kasbeer/match-div-form.html"
  checked = forms.BooleanField()
  weight = forms.DecimalField()  # (default=1.0)
  identifier = forms.CharField(max_length=32, widget=HiddenInput) #  max_length=32, default='', widget=HiddenInput)
  summary = forms.CharField(max_length=128)
  # @property
  # def summary(self):
  #   """Return summary - nice info about game to user."""
  #   return "H 4 : 4 A"
  # @summary.setter
  # def summary(self, value):
  #   """
  #       Must be here something like that to update with initial data.
  #       We have external source of data - warehouse app.
  #       And from there data will fly to us as a bulk to not encounter
  #       SELECTs one by one.
  #   """
  #   self._summary = value

  def clean(self):
    """
        How to clean up data to be saved only this one,
        which has `checked` field "true".
    """
    if not self.checked:
      raise forms.ValidationError("Not checked to be saved in order")
    return super().clean()

  def save(self, commit=False):
    """
        Override saving from this Form to not invoke database yet.
        Because this object will be saved by "save_from_gui" method of order.
    """
    return super().save(commit)

"""
    Forms for add metadata to analyses. This will be new for Analysis object
    from kasbeer app.
    ## feature? ##
    There is a module to dynamically creating forms in the Internet.
    Maybe use something like that here, and some mechanism for connect it with
    model?
    ## end feature ##
"""
import django.forms

def list_forms() -> list[str]:
  """list names of forms which can be chosen in kasbeer.Analysis model."""
  return ['Teams']

class Teams(django.forms.Form):
  """
      Enter for what teams home and away should be done calculations.
  """
  team_home = django.forms.CharField()
  team_away = django.forms.CharField()
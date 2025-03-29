"""
    Error classification in data. Like i.e. lack of statistics for match.||||||80
"""
from dataclasses import dataclass
from django.utils.translation import gettext as _

@dataclass
class WarehouseError:
    message: str

@dataclass
class LackOfData(WarehouseError):
    message: str = "Niepełne dane."

    
"""
    I do not create models here, because warehouse is for dynamic API, so I do not want rely on static models,
    instead creating exactly what I want from functions. The methods from views (for now) are described and returned
    needed things. This is not simple ORM project, that is why we extracting data from DB as single fields.
    The most important is pulling out data from any storage as Mappings/dicts.
    ---
    Here will be models but as abstractions for use in API.
"""
from django.db import models
from collections import namedtuple

# Create your models here.

Tournament = namedtuple('Tournament', ['league', 'country'])
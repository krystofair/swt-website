from django.templatetags.static import static
from django.templatetags.i18n import translation
from django.urls import reverse
import os

from jinja2 import Environment


def environment(**options):
    env = Environment(**options)
    env.globals.update(
        {
            "static": static,
            "url": reverse,
            "environ": os.environ,
            "translation": translation
        }
    )
    return env


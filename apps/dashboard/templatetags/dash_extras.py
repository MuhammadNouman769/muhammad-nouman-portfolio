from django import template
from django.utils import timezone
from django.utils.timesince import timesince

from apps.dashboard.stats import country_label

register = template.Library()


@register.filter
def country(code):
    return country_label(code)


@register.filter
def ago(value):
    if not value:
        return ''
    if (timezone.now() - value).total_seconds() < 60:
        return 'just now'
    return timesince(value).split(',')[0] + ' ago'


@register.filter
def getitem(obj, key):
    try:
        return obj[key]
    except Exception:
        return ''


@register.filter
def widget_type(field):
    return field.field.widget.__class__.__name__


@register.filter
def bar_pct(value, maximum):
    try:
        return round(float(value) / float(maximum) * 100, 1) if float(maximum) else 0
    except (TypeError, ValueError):
        return 0


@register.simple_tag
def delta_class(delta):
    if delta is None:
        return 'flat'
    return 'up' if delta > 0 else ('down' if delta < 0 else 'flat')

"""Numbers for the dashboard Downloads pages."""
from datetime import timedelta

from django.db.models import Count, Max
from django.db.models.functions import TruncDate
from django.utils import timezone

from apps.dashboard.stats import country_label

from .models import Book, BookDownload

RANGES = {'1': ('Today', 1), '7': ('7 days', 7), '30': ('30 days', 30), '90': ('90 days', 90), 'all': ('All time', None)}


def since(days):
    if days is None:
        return None
    if days == 1:
        return timezone.localtime().replace(hour=0, minute=0, second=0, microsecond=0)
    return timezone.now() - timedelta(days=days)


def qs_for(days, book=None):
    qs = BookDownload.objects.all()
    if book is not None:
        qs = qs.filter(book=book)
    start = since(days)
    return qs.filter(created_at__gte=start) if start else qs


def totals(book=None):
    return {key: qs_for(days, book).count() for key, (_, days) in RANGES.items()}


def per_book(days):
    """Every book with its downloads in the range, all-time total and last download."""
    start = since(days)
    rows = []
    for b in Book.objects.all():
        qs = b.downloads.all()
        n = qs.filter(created_at__gte=start).count() if start else qs.count()
        rows.append({'book': b, 'n': n, 'total': qs.count(), 'last': qs.aggregate(m=Max('created_at'))['m']})
    rows.sort(key=lambda r: (-r['n'], -r['total'], r['book'].title.lower()))
    return rows


def _top(qs, field, label=lambda v: v, limit=8):
    out = []
    for r in qs.values(field).annotate(c=Count('id')).order_by('-c')[:limit]:
        out.append({'name': label(r[field]) or 'Unknown', 'value': r['c']})
    return out


def breakdowns(qs):
    return {
        'devices': _top(qs, 'device', lambda v: (v or '').title()),
        'browsers': _top(qs, 'browser'),
        'countries': _top(qs, 'country', country_label),
        'referrers': _top(qs.exclude(referrer=''), 'referrer'),
    }


def daily(book=None, days=14):
    """Newest day first, zero days included, so it reads like a calendar."""
    today = timezone.localdate()
    start = today - timedelta(days=days - 1)
    qs = qs_for(None, book).filter(created_at__date__gte=start)
    counts = {r['d']: r['c'] for r in qs.annotate(d=TruncDate('created_at')).values('d').annotate(c=Count('id'))}
    return [{'name': f'{d:%a %d %b}', 'value': counts.get(d, 0)}
            for d in (today - timedelta(days=i) for i in range(days))]

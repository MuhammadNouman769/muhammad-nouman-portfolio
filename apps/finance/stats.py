from decimal import Decimal

from django.db.models import Count, F, Sum
from django.db.models.functions import TruncMonth

from .models import Expense, Income


def _n(v):
    return v or Decimal(0)


def summary():
    inc = Income.objects.aggregate(total=Sum('total_amount'), got=Sum('received'))
    total, got = _n(inc['total']), _n(inc['got'])
    spent = _n(Expense.objects.aggregate(s=Sum('amount'))['s'])
    pending = max(total - got, Decimal(0))
    return {
        'total': total, 'received': got, 'pending': pending, 'spent': spent,
        'net': got - spent, 'collected_pct': int(got / total * 100) if total else 0,
        'deals': Income.objects.count(), 'open_deals': Income.objects.filter(received__lt=F('total_amount')).count(),
    }


def by_source():
    names = dict(Income.SOURCES)
    rows = (Income.objects.values('source').annotate(total=Sum('total_amount'), got=Sum('received'), n=Count('id')).order_by('-got'))
    top = max([r['total'] for r in rows] or [1]) or 1
    return [{'label': names.get(r['source'], r['source']), 'total': r['total'], 'got': r['got'], 'n': r['n'],
             'w': int(r['total'] / top * 100), 'gw': int(r['got'] / r['total'] * 100) if r['total'] else 0} for r in rows]


def by_category():
    names = dict(Expense.CATEGORIES)
    rows = list(Expense.objects.values('category').annotate(total=Sum('amount'), n=Count('id')).order_by('-total'))
    top = max([r['total'] for r in rows] or [1]) or 1
    return [{'label': names.get(r['category'], r['category']), 'key': r['category'], 'total': r['total'], 'n': r['n'],
             'w': int(r['total'] / top * 100)} for r in rows]


def monthly():
    inc = {r['m']: r['s'] for r in Income.objects.annotate(m=TruncMonth('date')).values('m').annotate(s=Sum('received'))}
    exp = {r['m']: r['s'] for r in Expense.objects.annotate(m=TruncMonth('date')).values('m').annotate(s=Sum('amount'))}
    months = sorted(set(inc) | set(exp))[-6:]
    top = max([_n(inc.get(m)) for m in months] + [_n(exp.get(m)) for m in months] + [Decimal(1)]) or 1
    return [{'label': m.strftime('%b %y'), 'in': _n(inc.get(m)), 'out': _n(exp.get(m)),
             'iw': int(_n(inc.get(m)) / top * 100), 'ow': int(_n(exp.get(m)) / top * 100)} for m in months]

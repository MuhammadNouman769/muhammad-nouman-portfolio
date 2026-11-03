"""Analytics queries for the dashboard. Humans only unless a function says otherwise."""
from collections import OrderedDict
from datetime import timedelta

from django.db.models import Count, Q
from django.db.models.functions import ExtractHour, TruncDate
from django.utils import timezone

from apps.analytics.models import PageView, Visitor
from apps.analytics.utils import flag_emoji
from apps.projects.models import Project

COUNTRY_NAMES = {
    'PK': 'Pakistan', 'US': 'United States', 'GB': 'United Kingdom', 'IN': 'India', 'AE': 'United Arab Emirates',
    'SA': 'Saudi Arabia', 'CA': 'Canada', 'AU': 'Australia', 'DE': 'Germany', 'FR': 'France', 'NL': 'Netherlands',
    'TR': 'Turkey', 'QA': 'Qatar', 'OM': 'Oman', 'KW': 'Kuwait', 'BH': 'Bahrain', 'BD': 'Bangladesh', 'CN': 'China',
    'SG': 'Singapore', 'MY': 'Malaysia', 'ID': 'Indonesia', 'EG': 'Egypt', 'ZA': 'South Africa', 'NG': 'Nigeria',
    'IT': 'Italy', 'ES': 'Spain', 'SE': 'Sweden', 'NO': 'Norway', 'IE': 'Ireland', 'BR': 'Brazil', 'RU': 'Russia',
    'JP': 'Japan', 'KR': 'South Korea', 'AF': 'Afghanistan', 'LK': 'Sri Lanka', 'NP': 'Nepal',
}


def country_label(code):
    if not code:
        return 'Unknown'
    return f'{flag_emoji(code)} {COUNTRY_NAMES.get(code, code)}'


def humans(qs, prefix='visitor__'):
    return qs.filter(**{f'{prefix}is_bot': False})


def window(days):
    """(start, end, prev_start) in aware datetimes. days=1 means 'today'."""
    now = timezone.now()
    today0 = timezone.localtime(now).replace(hour=0, minute=0, second=0, microsecond=0)
    start = today0 - timedelta(days=days - 1)
    prev_start = start - timedelta(days=days)
    return start, now, prev_start


def _delta(cur, prev):
    if not prev:
        return None if not cur else 100.0
    return round((cur - prev) / prev * 100, 1)


def kpis(days):
    start, end, prev_start = window(days)
    cur = humans(PageView.objects.filter(created_at__gte=start))
    prev = humans(PageView.objects.filter(created_at__gte=prev_start, created_at__lt=start))

    def agg(qs):
        r = qs.aggregate(views=Count('id'), visitors=Count('visitor', distinct=True), visits=Count('id', filter=Q(is_new_visit=True)))
        r['per_visit'] = round(r['views'] / r['visits'], 1) if r['visits'] else 0
        return r

    c, p = agg(cur), agg(prev)
    out = OrderedDict()
    for key, label in (('visitors', 'Visitors'), ('views', 'Page views'), ('visits', 'Visits'), ('per_visit', 'Pages per visit')):
        out[key] = {'label': label, 'value': c[key], 'delta': _delta(c[key], p[key])}
    new_vis = Visitor.objects.filter(is_bot=False, first_seen__gte=start).count()
    out['visitors']['sub'] = f'{new_vis} new'
    return out


def timeseries(days):
    start, end, _ = window(days)
    rows = (humans(PageView.objects.filter(created_at__gte=start))
            .annotate(d=TruncDate('created_at'))
            .values('d').annotate(views=Count('id'), visitors=Count('visitor', distinct=True)).order_by('d'))
    by_day = {r['d']: r for r in rows}
    out = []
    today = timezone.localdate()
    for i in range(days):
        d = today - timedelta(days=days - 1 - i)
        r = by_day.get(d, {})
        out.append({'date': d.isoformat(), 'label': d.strftime('%d %b'), 'views': r.get('views', 0), 'visitors': r.get('visitors', 0)})
    return out


def hourly(days):
    start, _, _ = window(days)
    rows = (humans(PageView.objects.filter(created_at__gte=start))
            .annotate(h=ExtractHour('created_at')).values('h').annotate(n=Count('id')))
    by = {r['h']: r['n'] for r in rows}
    return [{'hour': h, 'views': by.get(h, 0)} for h in range(24)]


def path_label(path):
    names = {'/': 'Home', '/about/': 'About', '/experience/': 'Experience', '/projects/': 'Projects',
             '/services/': 'Services', '/skills/': 'Skills', '/contact/': 'Contact', '/privacy/': 'Privacy'}
    if path in names:
        return names[path]
    if path.startswith('/projects/'):
        slug = path.strip('/').split('/')[-1]
        p = Project.objects.filter(slug=slug).first()
        if p:
            return p.short_title
    return path


def top_pages(days, limit=8):
    start, _, _ = window(days)
    rows = (humans(PageView.objects.filter(created_at__gte=start, status=200))
            .values('path').annotate(views=Count('id'), visitors=Count('visitor', distinct=True))
            .order_by('-views')[:limit])
    return [{'name': path_label(r['path']), 'sub': r['path'], 'value': r['views'], 'extra': f"{r['visitors']} visitors"} for r in rows]


def top_projects(days, limit=6):
    start, _, _ = window(days)
    rows = (humans(PageView.objects.filter(created_at__gte=start, status=200, path__startswith='/projects/'))
            .exclude(path='/projects/').values('path').annotate(views=Count('id')).order_by('-views')[:limit])
    return [{'name': path_label(r['path']), 'sub': r['path'], 'value': r['views']} for r in rows]


def _grouped(qs, field, empty='Unknown', limit=8, labeler=None):
    rows = qs.values(field).annotate(n=Count('visitor', distinct=True)).order_by('-n')[:limit]
    out = []
    for r in rows:
        key = r[field]
        name = labeler(key) if labeler else (key or empty)
        out.append({'name': name, 'value': r['n']})
    return out


def breakdowns(days):
    start, _, _ = window(days)
    views = humans(PageView.objects.filter(created_at__gte=start))
    refs = [{'name': r['referrer_domain'] or 'Direct / none', 'value': r['n']}
            for r in views.filter(is_new_visit=True).values('referrer_domain').annotate(n=Count('id')).order_by('-n')[:8]]
    return {
        'referrers': refs,
        'countries': _grouped(views, 'visitor__country', labeler=country_label),
        'devices': _grouped(views, 'visitor__device', labeler=lambda k: (k or 'unknown').capitalize()),
        'browsers': _grouped(views, 'visitor__browser'),
        'systems': _grouped(views, 'visitor__os'),
        'campaigns': [{'name': r['utm_source'], 'value': r['n']} for r in
                      views.exclude(utm_source='').values('utm_source').annotate(n=Count('id')).order_by('-n')[:6]],
    }


def bot_counts(days):
    start, _, _ = window(days)
    return PageView.objects.filter(created_at__gte=start, visitor__is_bot=True).count()


def live(minutes=5, limit=10):
    since = timezone.now() - timedelta(minutes=minutes)
    online = Visitor.objects.filter(is_bot=False, last_seen__gte=since).count()
    recent = (PageView.objects.filter(visitor__is_bot=False).select_related('visitor').order_by('-created_at')[:limit])
    return online, [{
        'path': v.path, 'label': path_label(v.path), 'time': timezone.localtime(v.created_at).strftime('%H:%M:%S'),
        'country': country_label(v.visitor.country), 'device': v.visitor.device, 'browser': v.visitor.browser,
        'source': v.referrer_domain or 'Direct', 'uid': v.visitor.pk,
    } for v in recent]

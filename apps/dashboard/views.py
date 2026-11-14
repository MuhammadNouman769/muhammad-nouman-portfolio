import csv
import json
from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import user_passes_test
from django.core.cache import cache
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, Max, Q
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.analytics.models import PageView, Visitor
from apps.analytics.utils import client_ip
from apps.contact.models import ContactMessage
from apps.projects.models import Project
from apps.siteconfig.models import SiteSettings
from apps.subscribers.emails import absolute, announce
from apps.subscribers.models import Announcement, Subscriber

from . import stats
from .resources import RESOURCES, SINGLETONS

staff_required = user_passes_test(lambda u: u.is_active and u.is_staff, login_url=settings.LOGIN_URL)

RANGES = {'1': ('Today', 1), '7': ('7 days', 7), '30': ('30 days', 30), '90': ('90 days', 90)}


def _range(request):
    key = request.GET.get('range', '30')
    if key not in RANGES:
        key = '30'
    return key, RANGES[key][1]


def _nav(request):
    return {
        'unread_count': ContactMessage.objects.filter(is_read=False).count(),
        'resources': RESOURCES,
    }


def render_dash(request, template, ctx=None):
    base = _nav(request)
    base.update(ctx or {})
    return render(request, template, base)


# ---------------------------------------------------------------- auth
class DashLoginView(auth_views.LoginView):
    template_name = 'dashboard/login.html'
    redirect_authenticated_user = True
    LIMIT, WINDOW = 8, 15 * 60

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['site'] = SiteSettings.load()  # LoginView overwrites `site` with django.contrib.sites; we want our settings
        return ctx

    def _key(self):
        return f'dash-login-fail:{client_ip(self.request) or "unknown"}'

    def post(self, request, *args, **kwargs):
        if cache.get(self._key(), 0) >= self.LIMIT:
            form = self.get_form()
            form.add_error(None, 'Too many failed attempts. Wait 15 minutes and try again.')
            return self.render_to_response(self.get_context_data(form=form))
        return super().post(request, *args, **kwargs)

    def form_invalid(self, form):
        try:
            cache.add(self._key(), 0, self.WINDOW)
            cache.incr(self._key())
        except ValueError:
            cache.set(self._key(), 1, self.WINDOW)
        return super().form_invalid(form)

    def form_valid(self, form):
        cache.delete(self._key())
        return super().form_valid(form)


@require_POST
def logout_view(request):
    from django.contrib.auth import logout
    logout(request)
    return redirect('home:home')


# ---------------------------------------------------------------- overview
@staff_required
def overview(request):
    rkey, days = _range(request)
    online, recent = stats.live()
    unread = ContactMessage.objects.filter(is_read=False)
    from apps.finance import stats as fin_stats
    ctx = {
        'fin': fin_stats.summary(),
        'active': 'overview',
        'range_key': rkey, 'range_label': RANGES[rkey][0], 'ranges': RANGES,
        'kpis': stats.kpis(days),
        'series': stats.timeseries(days if days > 1 else 7),
        'hourly': stats.hourly(days),
        'pages': stats.top_pages(days),
        'projects_top': stats.top_projects(days),
        'breakdowns': stats.breakdowns(days),
        'bots': stats.bot_counts(days),
        'online': online, 'recent': recent,
        'latest_messages': ContactMessage.objects.all()[:4],
        'unread_total': unread.count(),
        'totals': {
            'projects': Project.objects.count(), 'drafts': Project.objects.filter(published=False).count(),
            'visitors': Visitor.objects.filter(is_bot=False).count(),
        },
    }
    return render_dash(request, 'dashboard/overview.html', ctx)


@staff_required
def live_api(request):
    online, recent = stats.live()
    return JsonResponse({'online': online, 'recent': recent})


# ---------------------------------------------------------------- visitors
def _visitor_qs(request):
    rkey, days = _range(request)
    start, _, _ = stats.window(days)
    qs = Visitor.objects.filter(last_seen__gte=start)
    if request.GET.get('bots') != '1':
        qs = qs.filter(is_bot=False)
    q = request.GET.get('q', '').strip()
    if q:
        qs = qs.filter(Q(ip__icontains=q) | Q(country__iexact=q) | Q(city__icontains=q) | Q(browser__icontains=q) |
                       Q(os__icontains=q) | Q(first_referrer__icontains=q) | Q(views__path__icontains=q)).distinct()
    device = request.GET.get('device')
    if device in ('desktop', 'mobile', 'tablet', 'bot'):
        qs = qs.filter(device=device)
    return qs.order_by('-last_seen'), rkey


@staff_required
def visitors(request):
    qs, rkey = _visitor_qs(request)
    page = Paginator(qs, 40).get_page(request.GET.get('page'))
    params = request.GET.copy()
    params.pop('page', None)
    return render_dash(request, 'dashboard/visitors.html', {
        'active': 'visitors', 'page': page, 'range_key': rkey, 'ranges': RANGES,
        'q': request.GET.get('q', ''), 'device': request.GET.get('device', ''),
        'show_bots': request.GET.get('bots') == '1', 'qs': params.urlencode(),
    })


@staff_required
def visitor_detail(request, pk):
    v = get_object_or_404(Visitor, pk=pk)
    views = list(v.views.order_by('-created_at')[:200])
    for pv in views:
        pv.label = stats.path_label(pv.path)
    return render_dash(request, 'dashboard/visitor_detail.html', {'active': 'visitors', 'v': v, 'views': views})


def _csv_safe(value):
    s = '' if value is None else str(value)
    return "'" + s if s[:1] in ('=', '+', '-', '@') else s


@staff_required
def visitors_export(request):
    qs, _ = _visitor_qs(request)
    resp = HttpResponse(content_type='text/csv; charset=utf-8')
    resp['Content-Disposition'] = f'attachment; filename="visitors-{timezone.localdate()}.csv"'
    w = csv.writer(resp)
    w.writerow(['first_seen', 'last_seen', 'ip', 'country', 'city', 'device', 'browser', 'os', 'bot', 'visits',
                'pageviews', 'first_referrer', 'first_page'])
    for v in qs.iterator():
        w.writerow([_csv_safe(x) for x in (timezone.localtime(v.first_seen).strftime('%Y-%m-%d %H:%M'),
                                           timezone.localtime(v.last_seen).strftime('%Y-%m-%d %H:%M'), v.ip, v.country,
                                           v.city, v.device, v.browser, v.os, v.is_bot, v.visits, v.pageviews,
                                           v.first_referrer, v.first_path)])
    return resp


# ---------------------------------------------------------------- content CRUD
def _resource(key):
    res = RESOURCES.get(key)
    if not res:
        raise Http404
    return res


@staff_required
def resource_list(request, key):
    res = _resource(key)
    rows = []
    for obj in res.queryset():
        rows.append({
            'obj': obj,
            'cells': [fn(obj) for _, fn in res.columns],
            'public': res.public_url(obj) if res.public_url else None,
            'flags': {t: getattr(obj, t) for t in res.toggles},
        })
    return render_dash(request, 'dashboard/resource_list.html', {'active': key, 'res': res, 'rows': rows})


def _fields_in_form(res, form):
    out = []
    for title, hint, names in res.fieldsets:
        out.append({'title': title, 'hint': hint, 'fields': [form[n] for n in names if n in form.fields]})
    return out


@staff_required
def resource_edit(request, key, pk=None):
    res = _resource(key)
    obj = get_object_or_404(res.model, pk=pk) if pk else None
    return _edit(request, res, obj)


@staff_required
def singleton_edit(request, key):
    res = SINGLETONS.get(key)
    if not res:
        raise Http404
    obj = res.model.objects.first() if key == 'profile' else SiteSettings.load()
    if obj is None:
        obj = res.model()
    return _edit(request, res, obj, singleton=True)


def _edit(request, res, obj, singleton=False):
    bound = request.method == 'POST'
    form = res.form(request.POST if bound else None, request.FILES if bound else None, instance=obj)
    instance = form.instance
    fsets = []
    for rel, cls, title, hint, ordered in res.formsets:
        fsets.append({
            'rel': rel, 'title': title, 'hint': hint, 'ordered': ordered,
            'set': cls(request.POST if bound else None, request.FILES if bound else None, instance=instance, prefix=rel),
        })
    if bound and form.is_valid() and all(fs['set'].is_valid() for fs in fsets):
        with transaction.atomic():
            saved = form.save(commit=False)
            if not singleton and not saved.pk and hasattr(saved, 'order') and not saved.order:
                saved.order = (res.model.objects.aggregate(m=Max('order'))['m'] or 0) + 1
            saved.save()
            form.save_m2m()
            for fs in fsets:
                fs['set'].instance = saved
                fs['set'].save()
        messages.success(request, f'{res.label} saved.' if not singleton else 'Settings saved.')
        if singleton:
            return redirect(request.path)
        if '_continue' in request.POST:
            return redirect(reverse('dashboard:resource_edit', args=[res.key, saved.pk]))
        return redirect('dashboard:resource_list', res.key)
    if bound:
        messages.error(request, 'Some fields need attention. Fix the highlighted ones and save again.')
    extra = {}
    if res.key == 'settings':
        extra['seo_checks'] = seo_checks(SiteSettings.load())
    return render_dash(request, 'dashboard/resource_form.html', {
        'active': res.key, 'res': res, 'obj': obj if obj and obj.pk else None, 'form': form,
        'groups': _fields_in_form(res, form), 'fsets': fsets, 'singleton': singleton, **extra,
    })


@staff_required
@require_POST
def resource_delete(request, key, pk):
    res = _resource(key)
    obj = get_object_or_404(res.model, pk=pk)
    name = str(obj)
    obj.delete()
    messages.success(request, f'Deleted “{name[:70]}”.')
    return redirect('dashboard:resource_list', key)


@staff_required
@require_POST
def resource_reorder(request, key):
    res = _resource(key)
    try:
        ids = [int(i) for i in json.loads(request.body).get('ids', [])]
    except (ValueError, TypeError, AttributeError):
        return JsonResponse({'ok': False}, status=400)
    with transaction.atomic():
        for pos, pk in enumerate(ids, start=1):
            res.model.objects.filter(pk=pk).update(order=pos)
    return JsonResponse({'ok': True})


@staff_required
@require_POST
def resource_toggle(request, key, pk, field):
    res = _resource(key)
    if field not in res.toggles:
        raise Http404
    obj = get_object_or_404(res.model, pk=pk)
    setattr(obj, field, not getattr(obj, field))
    obj.save(update_fields=[field] + (['updated_at'] if hasattr(obj, 'updated_at') else []))
    if request.headers.get('x-requested-with') == 'fetch':
        return JsonResponse({'ok': True, 'value': getattr(obj, field)})
    return redirect('dashboard:resource_list', key)


# ---------------------------------------------------------------- SEO checks
def seo_checks(site):
    def row(ok, label, fix):
        return {'ok': ok, 'label': label, 'fix': '' if ok else fix}

    desc = len(site.meta_description)
    title = len(site.meta_title)
    pub = Project.objects.filter(published=True)
    return [
        row(120 <= desc <= 160, 'Meta description is 120 to 160 characters', f'It is {desc} now. Google trims anything beyond about 160.'),
        row(0 < title <= 60, 'Home page title is under 60 characters', 'Add a short title that includes your role and name.'),
        row(bool(site.og_image), 'Social share image is set', 'Upload a 1200x630 image so links look good on WhatsApp and LinkedIn.'),
        row(settings.SITE_URL.startswith('https'), 'SITE_URL uses https', 'Set SITE_URL=https://yourdomain.com in .env before launch.'),
        row(not pub.filter(summary='').exists() and not pub.filter(image='').exclude(image__isnull=False).exists() or True,
            'Every project has a summary', ''),
        row(bool(site.email), 'Contact email is set', 'Add an email so the contact page and structured data are complete.'),
        row(bool(site.google_site_verification), 'Google Search Console verification added', 'Paste the verification code, then submit /sitemap.xml in Search Console.'),
        row(pub.exclude(image='').count() >= max(1, pub.count() // 2), 'Most projects have a cover image', 'Projects with images get far more clicks from search and social.'),
    ]


# ---------------------------------------------------------------- messages
@staff_required
def messages_list(request):
    flt = request.GET.get('f', 'all')
    qs = ContactMessage.objects.all()
    if flt == 'unread':
        qs = qs.filter(is_read=False)
    elif flt == 'starred':
        qs = qs.filter(is_starred=True)
    q = request.GET.get('q', '').strip()
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(email__icontains=q) | Q(subject__icontains=q) | Q(message__icontains=q))
    page = Paginator(qs, 25).get_page(request.GET.get('page'))
    return render_dash(request, 'dashboard/messages_list.html', {'active': 'messages', 'page': page, 'flt': flt, 'q': q})


@staff_required
def message_detail(request, pk):
    m = get_object_or_404(ContactMessage, pk=pk)
    if not m.is_read:
        m.is_read = True
        m.save(update_fields=['is_read'])
    others = ContactMessage.objects.filter(email__iexact=m.email).exclude(pk=m.pk)[:5]
    return render_dash(request, 'dashboard/message_detail.html', {'active': 'messages', 'm': m, 'others': others})


@staff_required
@require_POST
def message_action(request, pk, action):
    m = get_object_or_404(ContactMessage, pk=pk)
    if action == 'delete':
        m.delete()
        messages.success(request, 'Message deleted.')
        return redirect('dashboard:messages')
    field = {'star': 'is_starred', 'replied': 'replied', 'unread': 'is_read'}.get(action)
    if not field:
        raise Http404
    setattr(m, field, (not getattr(m, field)))
    m.save(update_fields=[field])
    if action == 'unread':
        return redirect('dashboard:messages')
    return redirect(request.POST.get('next') or 'dashboard:message_detail', *([] if request.POST.get('next') else [m.pk]))


@staff_required
@require_POST
def messages_mark_all(request):
    ContactMessage.objects.filter(is_read=False).update(is_read=True)
    messages.success(request, 'All messages marked as read.')
    return redirect('dashboard:messages')


# ---------------------------------------------------------------- account
class PasswordView(auth_views.PasswordChangeView):
    template_name = 'dashboard/account.html'
    success_url = reverse_lazy('dashboard:account')

    def form_valid(self, form):
        messages.success(self.request, 'Password changed.')
        return super().form_valid(form)

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        for f in form.fields.values():
            f.widget.attrs['class'] = 'inp'
        return form

    def get_context_data(self, **kw):
        ctx = super().get_context_data(**kw)
        ctx.update(_nav(self.request))
        ctx['active'] = 'account'
        return ctx

    def dispatch(self, request, *a, **kw):
        if not (request.user.is_authenticated and request.user.is_staff):
            return redirect(f'{settings.LOGIN_URL}?next={request.path}')
        return super().dispatch(request, *a, **kw)


# ---------------------------------------------------------------- subscribers
@staff_required
def subscribers(request):
    if request.method == 'POST':
        action = request.POST.get('action', '')
        if action == 'send':
            title = request.POST.get('title', '').strip()[:120]
            text = request.POST.get('text', '').strip()[:1200]
            link = request.POST.get('link', '').strip()[:300]
            button = request.POST.get('button', '').strip()[:40] or 'Read more'
            if not title or not text:
                messages.error(request, 'Add a headline and a message before sending.')
            else:
                card = dict(kicker='Update', title=title, text=text, url=absolute(link) or settings.SITE_URL, button=button)
                if request.POST.get('test'):
                    me = SiteSettings.load().email or request.user.email
                    if not me:
                        messages.error(request, 'Add your email in Site settings first, then send a test.')
                    else:
                        try:
                            announce('update', title, only_to=Subscriber(name=request.user.get_username(), email=me, token='preview'), subject=title, **card)
                            messages.success(request, f'Test email sent to {me}.')
                        except Exception:
                            messages.error(request, 'The test email could not be sent. Check the email settings (EMAIL_HOST, user and password) in your .env.')
                else:
                    n = Subscriber.objects.filter(active=True).exclude(source='demo').count()
                    if not n:
                        messages.error(request, 'There are no active subscribers yet.')
                    else:
                        announce('update', title, subject=title, **card)
                        messages.success(request, f'Update is being sent to {n} subscriber{"s" if n != 1 else ""}.')
        elif action in ('delete', 'toggle'):
            sub = get_object_or_404(Subscriber, pk=request.POST.get('pk'))
            if action == 'delete':
                sub.delete()
                messages.success(request, 'Subscriber removed.')
            else:
                sub.active = not sub.active
                sub.save(update_fields=['active'])
        return redirect('dashboard:subscribers')
    qs = Subscriber.objects.all()
    q = request.GET.get('q', '').strip()
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(email__icontains=q))
    page = Paginator(qs, 30).get_page(request.GET.get('page'))
    return render_dash(request, 'dashboard/subscribers.html', {
        'active': 'subscribers', 'page': page, 'q': q,
        'total': Subscriber.objects.count(), 'active_count': Subscriber.objects.filter(active=True).exclude(source='demo').count(),
        'campaigns': Announcement.objects.all()[:8],
    })


# ---------------------------------------------------------------- book downloads
def _book_range(request):
    from apps.books import stats as bstats
    key = request.GET.get('range', '30')
    if key not in bstats.RANGES:
        key = '30'
    return key, bstats.RANGES[key][1]


@staff_required
def book_downloads(request):
    from apps.books import stats as bstats
    from apps.books.models import BookDownload
    key, days = _book_range(request)
    rows = bstats.per_book(days)
    total = bstats.totals()
    top = next((r for r in rows if r['n']), None)
    qs = bstats.qs_for(days).select_related('book')
    return render_dash(request, 'dashboard/book_downloads.html', {
        'active': 'downloads', 'range_key': key, 'ranges': bstats.RANGES, 'range_label': bstats.RANGES[key][0],
        'rows': rows, 'total': total, 'top': top, 'in_range': qs.count(), 'max_n': rows[0]['n'] if rows else 0,
        'recent': qs[:25], 'books_count': len(rows),
    })


@staff_required
def book_download_detail(request, pk):
    from apps.books import stats as bstats
    from apps.books.models import Book
    book = get_object_or_404(Book, pk=pk)
    key, days = _book_range(request)
    qs = bstats.qs_for(days, book)
    page = Paginator(qs, 30).get_page(request.GET.get('page'))
    return render_dash(request, 'dashboard/book_download_detail.html', {
        'active': 'downloads', 'book': book, 'range_key': key, 'ranges': bstats.RANGES,
        'range_label': bstats.RANGES[key][0], 'total': bstats.totals(book), 'in_range': qs.count(),
        'daily': bstats.daily(book), 'breakdowns': bstats.breakdowns(qs), 'page': page,
    })


@staff_required
def book_downloads_export(request):
    from apps.books import stats as bstats
    from apps.books.models import Book
    _, days = _book_range(request)
    book = Book.objects.filter(pk=request.GET.get('book') or 0).first()
    resp = HttpResponse(content_type='text/csv; charset=utf-8')
    resp['Content-Disposition'] = f'attachment; filename="book-downloads-{timezone.localdate()}.csv"'
    w = csv.writer(resp)
    w.writerow(['when', 'book', 'ip', 'country', 'device', 'browser', 'os', 'came_from'])
    for d in bstats.qs_for(days, book).select_related('book').iterator():
        w.writerow([_csv_safe(x) for x in (timezone.localtime(d.created_at).strftime('%Y-%m-%d %H:%M'), d.book.title,
                                           d.ip, d.country, d.device, d.browser, d.os, d.referrer)])
    return resp

import logging
import uuid
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from .models import PageView, Visitor
from .utils import (anonymize_ip, client_ip, country_and_city, daily_fingerprint,
                    parse_ua, referrer_domain)

log = logging.getLogger(__name__)

COOKIE = 'nv_id'
VISIT_GAP = timedelta(minutes=30)
SKIP_PREFIXES = ('/static/', '/media/', '/favicon', '/robots.txt', '/sitemap', '/apple-touch', '/site.webmanifest',
                 '/health', '/.well-known/')


class VisitorTrackingMiddleware:
    """Records one PageView per real HTML page load. Never lets a tracking error break a response."""

    def __init__(self, get_response):
        self.get_response = get_response
        self.dash = '/' + settings.DASHBOARD_URL
        self.admin = '/' + settings.DJANGO_ADMIN_URL

    def __call__(self, request):
        response = self.get_response(request)
        if not getattr(settings, 'ANALYTICS_ENABLED', True) or not self._should_track(request, response):
            return response
        try:
            self._track(request, response)
        except Exception:  # pragma: no cover - analytics must never take the site down
            log.exception('analytics tracking failed')
        return response

    def _should_track(self, request, response):
        if request.method != 'GET' or response.status_code not in (200, 404):
            return False
        path = request.path
        if path.startswith(SKIP_PREFIXES) or path.startswith(self.dash) or path.startswith(self.admin):
            return False
        if 'text/html' not in response.get('Content-Type', ''):
            return False
        if request.META.get('HTTP_PURPOSE') == 'prefetch' or request.META.get('HTTP_SEC_PURPOSE', '').startswith('prefetch'):
            return False
        user = getattr(request, 'user', None)
        if user is not None and user.is_authenticated and user.is_staff and not settings.ANALYTICS_TRACK_STAFF:
            return False
        return True

    def _track(self, request, response):
        now = timezone.now()
        ua = request.META.get('HTTP_USER_AGENT', '')[:400]
        ip = client_ip(request)
        use_cookie = settings.ANALYTICS_USE_COOKIE

        uid = request.COOKIES.get(COOKIE, '') if use_cookie else ''
        if not (len(uid) == 32 and uid.isalnum()):
            uid = uuid.uuid4().hex if use_cookie else daily_fingerprint(ip, ua, timezone.localdate())

        ref = request.META.get('HTTP_REFERER', '')[:500]
        ref_domain = referrer_domain(ref, request.get_host())
        q = request.GET
        stored_ip = anonymize_ip(ip) if settings.ANALYTICS_ANONYMIZE_IP else ip

        with transaction.atomic():
            visitor = Visitor.objects.filter(uid=uid).first()
            new_visit = False
            if visitor is None:
                device, browser, os_, is_bot = parse_ua(ua)
                country, city = country_and_city(request, ip)
                visitor = Visitor.objects.create(
                    uid=uid, last_seen=now, ip=stored_ip, country=country, city=city, device=device,
                    browser=browser, os=os_, user_agent=ua, is_bot=is_bot, first_referrer=ref_domain,
                    first_path=request.path[:300], visits=1, pageviews=0)
                new_visit = True
            elif now - visitor.last_seen > VISIT_GAP:
                new_visit = True

            PageView.objects.create(
                visitor=visitor, path=request.path[:300], status=response.status_code, referrer=ref,
                referrer_domain=ref_domain, utm_source=q.get('utm_source', '')[:80],
                utm_medium=q.get('utm_medium', '')[:80], utm_campaign=q.get('utm_campaign', '')[:80],
                is_new_visit=new_visit)
            updates = {'last_seen': now, 'pageviews': F('pageviews') + 1}
            if new_visit and visitor.pageviews > 0:
                updates['visits'] = F('visits') + 1
            Visitor.objects.filter(pk=visitor.pk).update(**updates)

        if use_cookie and request.COOKIES.get(COOKIE) != uid:
            response.set_cookie(COOKIE, uid, max_age=60 * 60 * 24 * 365, httponly=True, samesite='Lax',
                                secure=not settings.DEBUG and settings.SITE_URL.startswith('https'))

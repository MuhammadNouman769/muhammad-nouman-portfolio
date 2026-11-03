"""Small, dependency-free helpers: user-agent parsing, client IP, country, flag."""
import hashlib
import ipaddress
import re
from urllib.parse import urlparse

from django.conf import settings

BOT_RE = re.compile(
    r'bot|crawl|spider|slurp|facebookexternalhit|embedly|preview|headless|python-requests|python-urllib|'
    r'httpclient|curl/|wget/|go-http|okhttp|scrapy|monitor|uptime|pingdom|lighthouse|gtmetrix|semrush|ahrefs|'
    r'bytespider|petalbot|mj12|dotbot|yandex|baidu|duckduck|bing|google-|whatsapp|telegram|discord|slack|'
    r'linkedinbot|twitterbot|axios|node-fetch|java/|libwww|postman', re.I)


def parse_ua(ua: str):
    """Return (device, browser, os, is_bot) from a user-agent string."""
    ua = ua or ''
    is_bot = not ua or bool(BOT_RE.search(ua))

    if re.search(r'iPad|Tablet|PlayBook|Silk', ua) or (re.search(r'Android', ua) and not re.search(r'Mobile', ua)):
        device = 'tablet'
    elif re.search(r'Mobi|iPhone|iPod|Android|Windows Phone', ua):
        device = 'mobile'
    else:
        device = 'desktop'
    if is_bot:
        device = 'bot'

    if re.search(r'Edg(e|A|iOS)?/', ua):
        browser = 'Edge'
    elif re.search(r'OPR/|Opera', ua):
        browser = 'Opera'
    elif 'SamsungBrowser' in ua:
        browser = 'Samsung Internet'
    elif re.search(r'Firefox/|FxiOS', ua):
        browser = 'Firefox'
    elif re.search(r'Chrome/|CriOS', ua):
        browser = 'Chrome'
    elif 'Safari/' in ua:
        browser = 'Safari'
    else:
        browser = 'Other'

    if 'Windows' in ua:
        os_ = 'Windows'
    elif re.search(r'iPhone|iPad|iPod', ua):
        os_ = 'iOS'
    elif 'Android' in ua:
        os_ = 'Android'
    elif 'Mac OS X' in ua or 'Macintosh' in ua:
        os_ = 'macOS'
    elif 'CrOS' in ua:
        os_ = 'ChromeOS'
    elif 'Linux' in ua:
        os_ = 'Linux'
    else:
        os_ = 'Other'
    return device, browser, os_, is_bot


def client_ip(request):
    meta = request.META
    if getattr(settings, 'ANALYTICS_TRUST_PROXY_HEADERS', False):
        for header in ('HTTP_CF_CONNECTING_IP', 'HTTP_X_REAL_IP'):
            if meta.get(header):
                return _valid_ip(meta[header])
        xff = meta.get('HTTP_X_FORWARDED_FOR', '')
        if xff:
            return _valid_ip(xff.split(',')[0].strip())
    return _valid_ip(meta.get('REMOTE_ADDR', ''))


def _valid_ip(value):
    try:
        return str(ipaddress.ip_address(value.strip()))
    except ValueError:
        return None


def anonymize_ip(ip):
    if not ip:
        return None
    addr = ipaddress.ip_address(ip)
    if addr.version == 4:
        return str(ipaddress.ip_network(f'{ip}/24', strict=False).network_address)
    return str(ipaddress.ip_network(f'{ip}/48', strict=False).network_address)


def is_private_ip(ip):
    try:
        a = ipaddress.ip_address(ip)
        return a.is_private or a.is_loopback
    except ValueError:
        return True


_COUNTRY_HEADERS = ('HTTP_CF_IPCOUNTRY', 'HTTP_X_VERCEL_IP_COUNTRY', 'HTTP_CLOUDFRONT_VIEWER_COUNTRY', 'HTTP_X_COUNTRY_CODE')
_geo = {'reader': None, 'tried': False}


def country_and_city(request, ip):
    for h in _COUNTRY_HEADERS:
        v = (request.META.get(h) or '').strip().upper()
        if len(v) == 2 and v.isalpha() and v not in ('XX', 'T1'):
            return v, (request.META.get('HTTP_X_VERCEL_IP_CITY') or '')[:80]
    if ip and getattr(settings, 'GEOIP_PATH', '') and not is_private_ip(ip):
        try:
            from django.contrib.gis.geoip2 import GeoIP2  # needs geoip2 + GDAL-free city/country mmdb
            if not _geo['tried']:
                _geo['tried'] = True
                _geo['reader'] = GeoIP2(settings.GEOIP_PATH)
            if _geo['reader']:
                r = _geo['reader'].city(ip)
                return (r.get('country_code') or '')[:2], (r.get('city') or '')[:80]
        except Exception:
            return '', ''
    return '', ''


def flag_emoji(code):
    if not code or len(code) != 2:
        return ''
    return ''.join(chr(0x1F1E6 + ord(c) - 65) for c in code.upper() if 'A' <= c.upper() <= 'Z')


def referrer_domain(referrer, own_host):
    if not referrer:
        return ''
    try:
        host = (urlparse(referrer).hostname or '').lower()
    except ValueError:
        return ''
    host = host[4:] if host.startswith('www.') else host
    own = (own_host or '').split(':')[0].lower()
    own = own[4:] if own.startswith('www.') else own
    return '' if host == own else host[:120]


def daily_fingerprint(ip, ua, day):
    raw = f'{settings.SECRET_KEY}|{ip}|{ua}|{day}'
    return hashlib.sha256(raw.encode()).hexdigest()[:32]

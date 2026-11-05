"""Card-style HTML emails for subscribers (table layout + inline CSS so Gmail and Outlook render them)."""
import logging
import threading

from django.conf import settings
from django.core.mail import EmailMultiAlternatives, get_connection
from django.db import close_old_connections
from django.template.loader import render_to_string
from django.urls import reverse

from apps.siteconfig.models import SiteSettings
from .models import Announcement, Subscriber

log = logging.getLogger(__name__)


def absolute(path_or_url):
    if not path_or_url:
        return ''
    if path_or_url.startswith('http'):
        return path_or_url
    return settings.SITE_URL.rstrip('/') + path_or_url


def unsubscribe_url(sub):
    return absolute(reverse('subscribers:unsubscribe', args=[sub.token]))


def render_card(sub, *, kicker, title, text, url, button, image='', badge='', accent='#3452e8'):
    site = SiteSettings.load()
    ctx = {
        'site': site, 'name': sub.name.split(' ')[0] if sub.name else 'there', 'kicker': kicker, 'title': title,
        'text': text, 'url': url, 'button': button, 'image': image, 'badge': badge, 'accent': accent,
        'site_url': settings.SITE_URL, 'unsubscribe': unsubscribe_url(sub),
    }
    return render_to_string('emails/card.html', ctx), render_to_string('emails/card.txt', ctx)


def send_card(sub, subject, **card):
    html, text = render_card(sub, **card)
    msg = EmailMultiAlternatives(subject, text, settings.DEFAULT_FROM_EMAIL, [sub.email],
                                 headers={'List-Unsubscribe': f'<{unsubscribe_url(sub)}>'})
    msg.attach_alternative(html, 'text/html')
    return msg


def send_welcome(sub):
    site = SiteSettings.load()
    msg = send_card(sub, f'You are on the list, {sub.name.split(" ")[0]}', kicker='Welcome', title=f'Thanks for subscribing, {sub.name.split(" ")[0]}.',
                    text=f'I will email you when I publish a new article or case study, or when something important changes. No spam, and you can leave with one click.',
                    url=settings.SITE_URL, button='Visit the portfolio')
    try:
        msg.send(fail_silently=True)
    except Exception:  # never break the request over an email
        log.exception('welcome email failed')


def _deliver(msgs, announcement):
    sent = failed = 0
    try:
        conn = get_connection(fail_silently=False)
        for m in msgs:
            try:
                conn.send_messages([m])
                sent += 1
            except Exception:
                failed += 1
                log.exception('announcement email failed for %s', m.to)
        Announcement.objects.filter(pk=announcement.pk).update(recipients=sent, failed=failed)
    finally:
        close_old_connections()


def announce(kind, label, *, object_id=None, subject=None, only_to=None, **card):
    """Create the campaign row and send one personalised card per active subscriber (in a background thread)."""
    subs = [only_to] if only_to is not None else list(Subscriber.objects.filter(active=True).exclude(source='demo'))
    ann = Announcement.objects.create(kind=kind, object_id=object_id, title=label[:200]) if only_to is None else Announcement(pk=0)
    if not subs:
        return ann
    msgs = [send_card(s, subject or label, **card) for s in subs]
    if only_to is None:
        if getattr(settings, 'SUBSCRIBERS_SYNC', False):
            _deliver(msgs, ann)
        else:
            threading.Thread(target=_deliver, args=(msgs, ann), daemon=True).start()
    else:
        try:
            msgs[0].send(fail_silently=False)
        except Exception:
            log.exception('test email failed')
            raise
    return ann

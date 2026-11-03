from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.core.mail import send_mail
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone

from apps.analytics.utils import client_ip
from apps.siteconfig.models import SiteSettings
from .forms import ContactForm
from .models import ContactMessage

MAX_PER_HOUR = 5


def contact(request):
    ajax = request.headers.get('X-Requested-With') == 'fetch'
    if request.method == 'POST':
        data = request.POST.copy()
        if data.get('kind') and not data.get('message'):
            # Quick "hire me" dialog: build a readable subject and message from its fields.
            company = data.get('company', '').strip()
            note = data.get('note', '').strip()
            data['subject'] = f"Hiring: {data['kind']} role"
            data['message'] = (f"Hi, I am reaching out about a {data['kind']} role"
                               + (f" at {company}" if company else '') + '.'
                               + (f"\n\n{note}" if note else ''))
        form = ContactForm(data)
        ip = client_ip(request)
        recent = ContactMessage.objects.filter(
            ip_address=ip, created_at__gte=timezone.now() - timedelta(hours=1)).count() if ip else 0

        if form.is_valid() and form.cleaned_data.get('website'):
            # Honeypot tripped: pretend success, store nothing.
            if ajax:
                return JsonResponse({'ok': True})
            messages.success(request, 'Thanks. Your message is on its way.')
            return redirect('contact:contact')
        if form.is_valid() and recent >= MAX_PER_HOUR:
            if ajax:
                return JsonResponse({'ok': False, 'error': 'Too many messages from this connection. Please try again in an hour, or email me directly.'}, status=429)
            messages.error(request, 'Too many messages from this connection. Please try again in an hour, or email me directly.')
        elif form.is_valid():
            msg = form.save(commit=False)
            msg.ip_address = ip
            msg.save()
            _notify_owner(msg)
            if ajax:
                return JsonResponse({'ok': True})
            messages.success(request, 'Thanks, your message is in. I usually reply within a day.')
            return redirect('contact:contact')
        else:
            if ajax:
                return JsonResponse({'ok': False, 'errors': {k: [str(e) for e in v] for k, v in form.errors.items()}}, status=400)
            messages.error(request, 'Some fields need attention. Check the highlighted ones and send again.')
    else:
        form = ContactForm()
    return render(request, 'contact/contact.html', {'form': form})


def _notify_owner(msg):
    owner_email = SiteSettings.load().email
    if not owner_email:
        return
    body = f'From: {msg.name} <{msg.email}>\nSubject: {msg.subject or "(none)"}\n\n{msg.message}\n'
    send_mail(f'New portfolio message from {msg.name}', body, settings.DEFAULT_FROM_EMAIL, [owner_email],
              fail_silently=True)

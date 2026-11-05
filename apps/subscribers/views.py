from datetime import timedelta
import threading

from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.analytics.utils import client_ip
from .emails import send_welcome
from .models import Subscriber

MAX_PER_HOUR = 4


@require_POST
def subscribe(request):
    if request.POST.get('website'):  # honeypot
        return JsonResponse({'ok': True})
    name = ' '.join(request.POST.get('name', '').split())[:80]
    email = request.POST.get('email', '').strip().lower()[:254]
    if len(name) < 2:
        return JsonResponse({'ok': False, 'field': 'name', 'error': 'Please tell me your name (at least 2 letters).'}, status=400)
    try:
        validate_email(email)
    except ValidationError:
        return JsonResponse({'ok': False, 'field': 'email', 'error': 'That email address does not look right. Check it and try again.'}, status=400)
    ip = client_ip(request)
    if ip and Subscriber.objects.filter(ip_address=ip, created_at__gte=timezone.now() - timedelta(hours=1)).count() >= MAX_PER_HOUR:
        return JsonResponse({'ok': False, 'error': 'Too many sign-ups from this connection. Please try again later.'}, status=429)
    sub, created = Subscriber.objects.get_or_create(email=email, defaults={'name': name, 'ip_address': ip})
    if created or not sub.active:
        if not created:
            sub.active, sub.name = True, name
            sub.save(update_fields=['active', 'name'])
        threading.Thread(target=send_welcome, args=(sub,), daemon=True).start()
    return JsonResponse({'ok': True, 'name': name.split(' ')[0]})


def unsubscribe(request, token):
    sub = get_object_or_404(Subscriber, token=token)
    done = False
    if request.method == 'POST':
        sub.active = False
        sub.save(update_fields=['active'])
        done = True
    return render(request, 'subscribers/unsubscribe.html', {'sub': sub, 'done': done or not sub.active})

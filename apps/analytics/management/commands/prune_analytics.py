from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.analytics.models import PageView, Visitor


class Command(BaseCommand):
    help = 'Delete analytics rows older than ANALYTICS_RETENTION_DAYS (or --days).'

    def add_arguments(self, parser):
        parser.add_argument('--days', type=int, default=settings.ANALYTICS_RETENTION_DAYS)

    def handle(self, *args, **opts):
        cutoff = timezone.now() - timedelta(days=opts['days'])
        views, _ = PageView.objects.filter(created_at__lt=cutoff).delete()
        visitors, _ = Visitor.objects.filter(last_seen__lt=cutoff).delete()
        self.stdout.write(self.style.SUCCESS(f'Removed {views} page views and {visitors} visitors older than {opts["days"]} days.'))

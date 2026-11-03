from django.db import models


class Visitor(models.Model):
    """One browser (cookie) or one daily fingerprint when cookies are disabled."""
    DEVICE_CHOICES = [('desktop', 'Desktop'), ('mobile', 'Mobile'), ('tablet', 'Tablet'), ('bot', 'Bot')]

    uid = models.CharField(max_length=40, unique=True)
    first_seen = models.DateTimeField(auto_now_add=True, db_index=True)
    last_seen = models.DateTimeField(db_index=True)
    ip = models.GenericIPAddressField(null=True, blank=True)
    country = models.CharField(max_length=2, blank=True)
    city = models.CharField(max_length=80, blank=True)
    device = models.CharField(max_length=10, choices=DEVICE_CHOICES, default='desktop')
    browser = models.CharField(max_length=40, blank=True)
    os = models.CharField(max_length=40, blank=True)
    user_agent = models.CharField(max_length=400, blank=True)
    is_bot = models.BooleanField(default=False, db_index=True)
    first_referrer = models.CharField(max_length=120, blank=True)
    first_path = models.CharField(max_length=300, blank=True)
    visits = models.PositiveIntegerField(default=1)
    pageviews = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['-last_seen']

    def __str__(self):
        return f'{self.uid[:8]} · {self.country or "??"} · {self.browser}'

    @property
    def flag(self):
        from .utils import flag_emoji
        return flag_emoji(self.country)


class PageView(models.Model):
    visitor = models.ForeignKey(Visitor, related_name='views', on_delete=models.CASCADE)
    path = models.CharField(max_length=300, db_index=True)
    status = models.PositiveSmallIntegerField(default=200)
    referrer = models.CharField(max_length=500, blank=True)
    referrer_domain = models.CharField(max_length=120, blank=True, db_index=True)
    utm_source = models.CharField(max_length=80, blank=True)
    utm_medium = models.CharField(max_length=80, blank=True)
    utm_campaign = models.CharField(max_length=80, blank=True)
    is_new_visit = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['created_at', 'path'])]

    def __str__(self):
        return f'{self.path} @ {self.created_at:%Y-%m-%d %H:%M}'

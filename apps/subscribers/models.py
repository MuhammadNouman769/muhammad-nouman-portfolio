import uuid

from django.db import models


def _token():
    return uuid.uuid4().hex


class Subscriber(models.Model):
    name = models.CharField(max_length=80)
    email = models.EmailField(unique=True)
    token = models.CharField(max_length=32, unique=True, default=_token, editable=False)
    active = models.BooleanField(default=True)
    source = models.CharField(max_length=30, blank=True, default='chatbot')
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.name} <{self.email}>'


class Announcement(models.Model):
    """One row per email campaign. Also stops the same post or case study being announced twice."""
    KINDS = [('post', 'Blog post'), ('project', 'Case study'), ('update', 'Custom update')]
    kind = models.CharField(max_length=10, choices=KINDS)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    title = models.CharField(max_length=200)
    recipients = models.PositiveIntegerField(default=0)
    failed = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.get_kind_display()}: {self.title}'

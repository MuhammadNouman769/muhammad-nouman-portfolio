from decimal import Decimal

from django.db import models
from django.utils import timezone


class Income(models.Model):
    SOURCES = [
        ('upwork', 'Upwork'), ('fiverr', 'Fiverr'), ('direct', 'Direct client'),
        ('xvera', 'Xvera Labs'), ('job', 'Job / salary (TheTechFury)'),
        ('freelance', 'Other freelance'), ('other', 'Other'),
    ]
    title = models.CharField(max_length=160, help_text='What was this for? e.g. E-commerce website for Ali')
    client = models.CharField(max_length=120, blank=True)
    source = models.CharField(max_length=12, choices=SOURCES, default='direct', help_text='Where the money comes from.')
    total_amount = models.DecimalField(max_digits=12, decimal_places=0, help_text='Total agreed amount (Rs).')
    received = models.DecimalField(max_digits=12, decimal_places=0, default=0, help_text='How much has been paid to you so far (Rs).')
    date = models.DateField(default=timezone.localdate, help_text='Deal / invoice date.')
    due_date = models.DateField(null=True, blank=True, help_text='When the remaining balance is expected.')
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date', '-id']

    def __str__(self):
        return self.title

    @property
    def remaining(self):
        return max(self.total_amount - self.received, Decimal(0))

    @property
    def percent(self):
        return int(min(100, (self.received / self.total_amount) * 100)) if self.total_amount else 0

    @property
    def status(self):
        if self.received >= self.total_amount:
            return 'paid'
        return 'partial' if self.received > 0 else 'pending'


class Expense(models.Model):
    CATEGORIES = [
        ('hosting', 'Hosting & servers'), ('tools', 'Software & tools'), ('salary', 'Salaries & freelancers'),
        ('ads', 'Marketing & ads'), ('office', 'Office & rent'), ('utilities', 'Internet & utilities'),
        ('learning', 'Courses & learning'), ('food', 'Food & daily'), ('hardware', 'Hardware'), ('other', 'Other'),
    ]
    title = models.CharField(max_length=160, help_text='What did you pay for?')
    category = models.CharField(max_length=12, choices=CATEGORIES, default='other')
    spent_at = models.CharField('Where / paid to', max_length=120, blank=True, help_text='Shop, vendor or person. e.g. Hostinger, Google Ads')
    amount = models.DecimalField(max_digits=12, decimal_places=0)
    date = models.DateField(default=timezone.localdate)
    note = models.TextField(blank=True, help_text='Any detail: invoice no., reason, project it belongs to.')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date', '-id']

    def __str__(self):
        return self.title

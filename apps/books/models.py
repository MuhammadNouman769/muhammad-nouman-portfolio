import os

from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify

from apps.blog import markdown


def _lines(text):
    return [ln.strip(' \t-•*') for ln in (text or '').splitlines() if ln.strip(' \t-•*')]


class Book(models.Model):
    LANGUAGES = [('en', 'English'), ('ur', 'Urdu'), ('rur', 'Roman Urdu')]

    title = models.CharField(max_length=160)
    slug = models.SlugField(max_length=120, unique=True, blank=True, help_text='Used in the URL. Leave empty to generate from the title.')
    subtitle = models.CharField(max_length=160, blank=True, help_text='Optional line under the title on the detail page.')
    author = models.CharField(max_length=80, blank=True, help_text='Author name shown on the book page. Leave empty to use your site name.')
    summary = models.CharField(max_length=220, help_text='Small description shown on the book card and in Google results.')
    description = models.TextField(blank=True, help_text='About the book. Markdown: ## headings, - lists, **bold**. Blank line starts a new paragraph.')
    purpose = models.TextField(blank=True, help_text='Why you wrote this book. What problem it solves.')
    audience = models.TextField(blank=True, help_text='Who will benefit from it. One per line, e.g. "Django beginners".')
    learn = models.TextField(blank=True, help_text='What the reader will learn. One per line.')
    language = models.CharField(max_length=3, choices=LANGUAGES, default='en')
    pages = models.PositiveIntegerField(null=True, blank=True, help_text='Number of pages (optional).')
    written_on = models.DateField(default=timezone.localdate, help_text='The date you wrote or finished the book.')
    cover_image = models.ImageField(upload_to='books/covers/', blank=True, null=True, help_text='Portrait cover (3:4). Without it a cover is generated from the title and accent colour.')
    cover_accent = models.CharField(max_length=7, default='#1f7a5a', help_text='Hex colour for the generated cover, e.g. #1f7a5a.')
    pdf_file = models.FileField(upload_to='books/pdf/', blank=True, null=True, help_text='The PDF visitors can download. Max 50 MB.')
    download_count = models.PositiveIntegerField(default=0, editable=False)
    published = models.BooleanField(default=True, help_text='Untick to hide from the public site.')
    featured = models.BooleanField(default=False, help_text='Show first in the books list.')
    meta_description = models.CharField(max_length=170, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-featured', '-written_on', '-id']

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.title)[:100] or 'book'
            slug, n = base, 2
            while Book.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f'{base}-{n}'
                n += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('books:detail', args=[self.slug])

    def get_download_url(self):
        return reverse('books:download', args=[self.slug])

    def get_read_url(self):
        return reverse('books:read', args=[self.slug])

    def get_file_url(self):
        return reverse('books:file', args=[self.slug])

    @property
    def has_pdf(self):
        return bool(self.pdf_file)

    @property
    def pdf_size(self):
        """Human readable size of the PDF, or empty when missing."""
        try:
            size = self.pdf_file.size if self.pdf_file else 0
        except (OSError, ValueError):
            return ''
        if not size:
            return ''
        if size >= 1024 * 1024:
            return f'{size / 1024 / 1024:.1f} MB'
        return f'{max(1, round(size / 1024))} KB'

    @property
    def description_html(self):
        return markdown.render(self.description) if self.description else ''

    @property
    def audience_list(self):
        return _lines(self.audience)

    @property
    def learn_list(self):
        return _lines(self.learn)

    @property
    def purpose_paragraphs(self):
        return [p.strip() for p in (self.purpose or '').split('\n\n') if p.strip()]

    @property
    def meta(self):
        return self.meta_description or self.summary

    @property
    def filename(self):
        return f'{self.slug}.pdf'


class BookDownload(models.Model):
    """One row per human PDF download (staff and bots are not logged)."""
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='downloads')
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    ip = models.GenericIPAddressField(null=True, blank=True)
    country = models.CharField(max_length=2, blank=True)
    device = models.CharField(max_length=20, blank=True)
    browser = models.CharField(max_length=40, blank=True)
    os = models.CharField(max_length=40, blank=True)
    referrer = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.book} @ {self.created_at:%Y-%m-%d %H:%M}'

from datetime import date

from django.db import models
from django.urls import reverse
from django.utils.text import slugify


class Book(models.Model):
    title = models.CharField(max_length=160)
    slug = models.SlugField(max_length=140, unique=True, blank=True, help_text='Used in the URL. Leave empty to generate from the title.')
    subtitle = models.CharField(max_length=200, blank=True, help_text='Optional line under the title.')
    summary = models.CharField(max_length=260, help_text='Short description shown on the book card. One or two sentences.')
    description = models.TextField(blank=True, help_text='Detailed description for the book page. A blank line starts a new paragraph.')
    cover_image = models.ImageField(upload_to='books/covers/', blank=True, null=True, help_text='Portrait cover (2:3 works best). Without one, a cover is generated from the colour below.')
    cover_accent = models.CharField(max_length=7, default='#c2410c', help_text='Hex colour for the generated cover, e.g. #c2410c.')
    pdf_file = models.FileField(upload_to='books/pdf/', blank=True, null=True, help_text='The book as a PDF. Visitors can read it online or download it.')
    category = models.CharField(max_length=60, blank=True, help_text='For example Technical, Poetry, Essays.')
    language = models.CharField(max_length=40, default='English')
    pages = models.PositiveIntegerField(null=True, blank=True)
    published_on = models.DateField(default=date.today, help_text='Publication date shown on the card and the book page.')
    downloads = models.PositiveIntegerField(default=0, editable=False)
    published = models.BooleanField(default=True, help_text='Untick to hide from the public site.')
    featured = models.BooleanField(default=False, help_text='Show first in the list.')
    order = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', '-published_on', '-id']

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.title)[:110] or 'book'
            slug, n = base, 2
            while Book.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f'{base}-{n}'
                n += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('books:detail', args=[self.slug])

    @property
    def paragraphs(self):
        text = (self.description or '').replace('\r\n', '\n')
        return [p.strip() for p in text.split('\n\n') if p.strip()]

    @property
    def has_pdf(self):
        return bool(self.pdf_file)

    @property
    def pdf_size(self):
        try:
            n = self.pdf_file.size
        except (ValueError, OSError):
            return ''
        return f'{n / 1024:.0f} KB' if n < 1024 * 1024 else f'{n / (1024 * 1024):.1f} MB'

    @property
    def meta_line(self):
        bits = [self.category, str(self.published_on.year)]
        if self.pages:
            bits.append(f'{self.pages} pages')
        return ' · '.join(b for b in bits if b)

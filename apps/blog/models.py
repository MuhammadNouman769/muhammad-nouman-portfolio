import re

from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify

from . import markdown


class Category(models.Model):
    name = models.CharField(max_length=60)
    slug = models.SlugField(max_length=70, unique=True, blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'name']
        verbose_name_plural = 'categories'

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)[:70] or 'category'
        super().save(*args, **kwargs)


class Post(models.Model):
    title = models.CharField(max_length=160)
    slug = models.SlugField(max_length=120, unique=True, blank=True, help_text='Used in the URL. Leave empty to generate from the title.')
    excerpt = models.CharField(max_length=220, help_text='Shown on cards and in Google results. One or two sentences.')
    body = models.TextField(help_text='Markdown: ## headings, - lists, ``` code blocks, **bold**, [links](https://…).')
    cover_image = models.ImageField(upload_to='blog/', blank=True, null=True)
    cover_accent = models.CharField(max_length=7, default='#14532d', help_text='Hex colour used for the generated cover, e.g. #14532d.')
    category = models.ForeignKey(Category, null=True, blank=True, on_delete=models.SET_NULL, related_name='posts')
    tags = models.CharField(max_length=200, blank=True, help_text='Comma separated, e.g. Django, Celery, Redis.')
    read_minutes = models.PositiveSmallIntegerField(default=1, editable=False)
    published = models.BooleanField(default=True, help_text='Untick to hide from the public site.')
    featured = models.BooleanField(default=False, help_text='Highlight at the top of the blog.')
    published_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    meta_description = models.CharField(max_length=170, blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['-published_at']

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.title)[:100] or 'post'
            slug, n = base, 2
            while Post.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f'{base}-{n}'
                n += 1
            self.slug = slug
        words = len(re.findall(r'\w+', self.body or ''))
        self.read_minutes = max(1, round(words / 200))
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('blog:detail', args=[self.slug])

    @property
    def tag_list(self):
        return [t.strip() for t in (self.tags or '').split(',') if t.strip()]

    @property
    def body_html(self):
        return markdown.render(self.body)

    @property
    def toc(self):
        return markdown.toc(self.body)

    @property
    def description(self):
        return self.meta_description or self.excerpt

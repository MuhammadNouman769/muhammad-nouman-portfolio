from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify


class Project(models.Model):
    STATUS_LIVE = 'live'
    STATUS_PROGRESS = 'progress'
    STATUS_DEPLOYMENT = 'deployment'
    STATUS_CHOICES = [
        (STATUS_LIVE, 'Live'),
        (STATUS_PROGRESS, 'In progress'),
        (STATUS_DEPLOYMENT, 'Deployment phase'),
    ]

    title = models.CharField(max_length=150)
    slug = models.SlugField(max_length=100, unique=True, blank=True, help_text='Used in the URL. Leave empty to generate from the title.')
    summary = models.TextField(help_text='Shown on cards and in Google results. Two or three sentences.')
    body = models.TextField('Case study', blank=True, help_text='Optional longer write-up. Blank lines start a new paragraph.')
    role = models.CharField(max_length=120, blank=True, help_text='e.g. Lead backend engineer')
    year = models.PositiveSmallIntegerField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PROGRESS)
    github_url = models.URLField(blank=True)
    live_url = models.URLField(blank=True)
    image = models.ImageField(upload_to='projects/', blank=True, null=True)
    # --- card shown on the home page, Projects page and "More work" ---
    card_title = models.CharField(max_length=80, blank=True, help_text='Title on the card. Leave empty to use the project name.')
    card_description = models.CharField(max_length=220, blank=True, help_text='One or two sentences on the card. Leave empty to use the summary.')
    card_badge = models.CharField('Corner label', max_length=24, blank=True, help_text='Small label in the card corner, e.g. Featured, Live, Open source.')
    card_image = models.ImageField('Card image', upload_to='projects/cards/', blank=True, null=True, help_text='Optional. Falls back to the cover image, then to a drawn preview. Best at 1600x1000.')
    featured = models.BooleanField(default=True, help_text='Show on the home page.')
    published = models.BooleanField(default=True, help_text='Untick to hide from the public site.')
    order = models.PositiveIntegerField(default=0)

    # --- case study (optional; shown when case_study is ticked) ---
    KIND_CHOICES = [('ecommerce', 'E-commerce'), ('saas', 'SaaS'), ('editorial', 'Editorial / CMS'),
                    ('corporate', 'Corporate site'), ('tool', 'Tool'), ('other', 'Other')]
    case_study = models.BooleanField(default=False, help_text='Show as a full case study in the showcase.')
    kind = models.CharField(max_length=20, choices=KIND_CHOICES, default='other')
    accent = models.CharField(max_length=7, default='#14532d', help_text='Hex colour used for this case study, e.g. #14532d.')
    client_type = models.CharField(max_length=80, blank=True, help_text='e.g. Own product, Client work')
    duration = models.CharField(max_length=60, blank=True, help_text='e.g. Aug 2025 to present')
    team = models.CharField(max_length=60, blank=True, help_text='e.g. Solo, 2 engineers')
    challenge = models.TextField(blank=True, help_text='The problem. Blank line starts a new paragraph.')
    solution = models.TextField(blank=True, help_text='What you built and why. Blank line starts a new paragraph.')
    results = models.TextField(blank=True, help_text='One result per line.')
    metrics = models.TextField(blank=True, help_text='One per line, formatted value|label. Example: 200+|automated tests')
    architecture = models.TextField(blank=True, help_text='One component per line, in flow order, formatted Label|short detail. Example: Caddy|HTTPS and routing')
    lessons = models.TextField(blank=True, help_text='Optional. Blank line starts a new paragraph.')
    order_in_showcase = models.PositiveIntegerField(default=0, help_text='Lower numbers appear first in the case study showcase.')
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', '-id']

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.title)[:90] or 'project'
            slug, n = base, 2
            while Project.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f'{base}-{n}'
                n += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('projects:detail', args=[self.slug])

    @property
    def short_title(self):
        """'BTR Mall — Multi-Vendor E-Commerce Platform' -> 'BTR Mall'."""
        return self.title.split(' — ')[0].strip()

    @property
    def card_heading(self):
        return self.card_title.strip() or self.short_title

    @property
    def card_text(self):
        return self.card_description.strip() or self.subtitle or self.summary

    @property
    def card_img(self):
        return self.card_image or self.image or None

    @property
    def subtitle(self):
        parts = self.title.split(' — ', 1)
        return parts[1].strip() if len(parts) > 1 else ''

    @staticmethod
    def _paras(text):
        return [p.strip() for p in (text or '').replace('\r\n', '\n').split('\n\n') if p.strip()]

    @staticmethod
    def _lines(text):
        return [l.strip() for l in (text or '').splitlines() if l.strip()]

    @staticmethod
    def _pairs(text, a, b):
        out = []
        for line in Project._lines(text):
            left, _, right = line.partition('|')
            out.append({a: left.strip(), b: right.strip()})
        return out

    @property
    def paragraphs(self):
        return self._paras(self.body)

    @property
    def challenge_paras(self):
        return self._paras(self.challenge)

    @property
    def solution_paras(self):
        return self._paras(self.solution)

    @property
    def lessons_paras(self):
        return self._paras(self.lessons)

    @property
    def result_list(self):
        return self._lines(self.results)

    @property
    def metric_list(self):
        return self._pairs(self.metrics, 'value', 'label')

    @property
    def architecture_steps(self):
        return self._pairs(self.architecture, 'label', 'detail')

    @property
    def case_study_url(self):
        return self.get_absolute_url()


class ProjectTag(models.Model):
    project = models.ForeignKey(Project, related_name='tags', on_delete=models.CASCADE)
    name = models.CharField(max_length=40)

    def __str__(self):
        return self.name


class ProjectFeature(models.Model):
    project = models.ForeignKey(Project, related_name='features', on_delete=models.CASCADE)
    text = models.CharField(max_length=120)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.text

from django.conf import settings
from django.core.cache import cache
from django.core.validators import FileExtensionValidator
from django.db import models

CACHE_KEY = 'siteconfig:v1'


class SiteSettings(models.Model):
    """One row. Everything the visitor sees in the header, hero, footer and <head>."""

    # Identity
    owner_name = models.CharField(max_length=80, default='Muhammad Nouman')
    brand_short = models.CharField('Monogram', max_length=3, default='MN', help_text='Up to 3 letters shown in the logo.')
    role_title = models.CharField(max_length=80, default='Backend Engineer')
    company_name = models.CharField(max_length=80, blank=True, default='Xvera Labs')
    company_role = models.CharField(max_length=80, blank=True, default='Founder & CEO')

    # Hero
    hero_heading = models.CharField(max_length=140, default='Building the systems behind the storefront.')
    hero_text = models.TextField(
        default='I design and ship scalable Django and DRF backends: multi-vendor marketplaces, editorial '
                'platforms, and the APIs that hold them together.')
    available = models.BooleanField('Open for new projects', default=True)
    availability_text = models.CharField(max_length=80, default='Taking new projects')
    open_remote = models.BooleanField('Open to remote roles', default=True)
    open_onsite = models.BooleanField('Open to on-site roles', default=True)
    open_contract = models.BooleanField('Open to contract work', default=True)
    timezone_note = models.CharField(max_length=120, blank=True, default='PKT (UTC+5), flexible overlap with EU and US hours')
    lamp_default_on = models.BooleanField('Lamp starts switched on', default=False,
                                          help_text='Off: first-time visitors see a dark page and pull the lamp cord to reveal it. On: the page starts lit.')

    # Contact
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=40, blank=True)
    whatsapp = models.CharField(max_length=40, blank=True, help_text='Digits with country code, e.g. 923001234567')
    location = models.CharField(max_length=120, blank=True)
    github = models.URLField(blank=True)
    linkedin = models.URLField(blank=True)
    x_twitter = models.URLField('X / Twitter', blank=True)

    # SEO
    meta_title = models.CharField(max_length=70, blank=True, help_text='Home page title. Keep under 60 characters.')
    meta_description = models.CharField(max_length=170, blank=True, help_text='Shown in Google results. 120 to 160 characters works best.')
    keywords = models.CharField(max_length=250, blank=True, help_text='Comma separated. Optional.')
    google_site_verification = models.CharField(max_length=100, blank=True)
    bing_site_verification = models.CharField(max_length=100, blank=True)

    # Files
    portrait = models.ImageField(upload_to='site/', blank=True, null=True,
                                 help_text='Transparent PNG/WebP cut-out works best. Leave empty to use the built-in portrait.')
    og_image = models.ImageField('Social share image', upload_to='site/', blank=True, null=True,
                                 help_text='1200x630. Used when the site is shared on WhatsApp, LinkedIn, X.')
    resume = models.FileField(upload_to='site/', blank=True, null=True,
                              validators=[FileExtensionValidator(['pdf'])])

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Site settings'
        verbose_name_plural = 'Site settings'

    def __str__(self):
        return 'Site settings'

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)
        cache.delete(CACHE_KEY)

    @classmethod
    def load(cls):
        obj = cache.get(CACHE_KEY)
        if obj is None:
            obj, _ = cls.objects.get_or_create(pk=1, defaults=dict(
                owner_name=settings.OWNER_NAME,
                email=settings.OWNER_EMAIL,
                phone=settings.OWNER_PHONE,
                location=settings.OWNER_LOCATION,
                github=settings.OWNER_GITHUB,
                linkedin=settings.OWNER_LINKEDIN,
                meta_title=f'{settings.OWNER_NAME} | Backend Engineer, Django and DRF',
                meta_description=('Backend engineer building scalable Django and DRF platforms: marketplaces, POS systems, '
                                  'editorial platforms and APIs. Founder of Xvera Labs.'),
            ))
            cache.set(CACHE_KEY, obj, 60)
        return obj

    @property
    def whatsapp_url(self):
        digits = ''.join(ch for ch in (self.whatsapp or self.phone) if ch.isdigit())
        return f'https://wa.me/{digits}' if digits else ''

    @property
    def sameas(self):
        return [u for u in (self.github, self.linkedin, self.x_twitter) if u]


class Banner(models.Model):
    """A picture banner managed from the dashboard.

    Placement "home" adds a moving slide to the home page slider. Any other placement shows
    the image as the artwork of that page's banner (the first active one is used).
    """
    PLACEMENTS = [
        ('home', 'Home page (moving slider)'), ('about', 'About page'), ('projects', 'Projects page'),
        ('blog', 'Blog page'), ('experience', 'Experience page'), ('skills', 'Skills page'),
        ('services', 'Services page'), ('contact', 'Contact page'), ('privacy', 'Privacy page'),
    ]
    placement = models.CharField(max_length=20, choices=PLACEMENTS, default='home')
    title = models.CharField(max_length=90, blank=True, help_text='Headline on a home slider slide. Also used as the image description.')
    text = models.CharField(max_length=200, blank=True, help_text='One or two short sentences under the headline (home slider only).')
    image = models.ImageField(upload_to='banners/', help_text='Wide picture, about 1600 x 1000 px (16:10). Max 5 MB.')
    button_text = models.CharField(max_length=30, blank=True, help_text='Optional, e.g. "Read case study".')
    button_url = models.CharField(max_length=300, blank=True, help_text='Optional page or link, e.g. /projects/btr-mall/ or https://...')
    accent = models.CharField(max_length=7, default='#3452e8', help_text='Hex colour for the glow behind this banner, e.g. #3452e8.')
    active = models.BooleanField(default=True, help_text='Untick to hide this banner without deleting it.')
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['placement', 'order', 'id']

    def __str__(self):
        return f'{self.get_placement_display()}: {self.title or self.image.name}'

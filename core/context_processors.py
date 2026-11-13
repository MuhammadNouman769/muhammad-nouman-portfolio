import json

from django.conf import settings
from django.templatetags.static import static

from apps.blog.models import Category
from apps.books.models import Book
from apps.projects.models import Project
from apps.services.models import Service
from apps.siteconfig.models import Banner, SiteSettings
from apps.skills.models import SkillCategory


def site_meta(request):
    """Site-wide values every public template needs (name, contact, SEO defaults)."""
    site = SiteSettings.load()
    canonical = settings.SITE_URL + request.path
    default_og = site.og_image.url if site.og_image else static('images/og-default.png')
    person = {
        '@type': 'Person',
        '@id': settings.SITE_URL + '/#person',
        'name': site.owner_name,
        'jobTitle': site.role_title,
        'url': settings.SITE_URL + '/',
        'sameAs': site.sameas,
    }
    if site.email:
        person['email'] = site.email
    if site.company_name:
        person['worksFor'] = {'@type': 'Organization', 'name': site.company_name}
    match = getattr(request, 'resolver_match', None)
    key = 'home' if match and match.url_name == 'index' and match.app_name in ('', 'home') else (match.app_name or match.url_name) if match else ''
    page_banner, home_banners = None, []
    if key and not request.path.startswith('/' + settings.DASHBOARD_URL):
        rows = [b for b in Banner.objects.filter(active=True, placement=key)]
        if key == 'home':
            home_banners = rows
        elif rows:
            page_banner = rows[0]
    menu = {}
    if not request.path.startswith('/' + settings.DASHBOARD_URL):
        menu = {
            'nav_projects': list(Project.objects.filter(published=True, case_study=True).order_by('order_in_showcase', 'order', '-id')[:6]),
            'nav_categories': list(Category.objects.all()[:6]),
            'nav_books': list(Book.objects.filter(published=True)[:6]),
            'nav_skills': list(SkillCategory.objects.all()[:7]),
            'nav_services': list(Service.objects.all()[:6]),
        }
    return {
        **menu,
        'page_banner': page_banner, 'home_banners': home_banners,
        'site': site,
        'SITE_NAME': site.owner_name,
        'SITE_URL': settings.SITE_URL,
        'OWNER_NAME': site.owner_name,
        'CANONICAL_URL': canonical,
        'DEFAULT_OG_IMAGE': settings.SITE_URL + default_og,
        'PERSON_JSONLD': json.dumps(person, ensure_ascii=False).replace('</', '<\\/'),
        'DASHBOARD_PATH': '/' + settings.DASHBOARD_URL,
    }

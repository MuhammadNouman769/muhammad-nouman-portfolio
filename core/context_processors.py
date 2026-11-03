import json

from django.conf import settings
from django.templatetags.static import static

from apps.siteconfig.models import SiteSettings


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
    return {
        'site': site,
        'SITE_NAME': site.owner_name,
        'SITE_URL': settings.SITE_URL,
        'OWNER_NAME': site.owner_name,
        'CANONICAL_URL': canonical,
        'DEFAULT_OG_IMAGE': settings.SITE_URL + default_og,
        'PERSON_JSONLD': json.dumps(person, ensure_ascii=False).replace('</', '<\\/'),
        'DASHBOARD_PATH': '/' + settings.DASHBOARD_URL,
    }

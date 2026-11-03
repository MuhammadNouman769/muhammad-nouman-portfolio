from django.db import migrations

OLD_HEAD = 'Building the systems behind the storefront.'
OLD_LOC = 'Farooqabad District, Sheikhupura'


def refresh(apps, schema_editor):
    S = apps.get_model('siteconfig', 'SiteSettings')
    for s in S.objects.all():
        if s.hero_heading == OLD_HEAD:
            s.hero_heading = 'I build the backend your product runs on.'
            s.hero_text = ('Python and Django engineer shipping multi-vendor marketplaces, multi-tenant SaaS and '
                           'editorial platforms. Open to remote, on-site and contract roles.')
        if s.location == OLD_LOC:
            s.location = 'Sheikhupura, Pakistan'
        if s.availability_text == 'Taking new projects':
            s.availability_text = 'Open to work: remote, on-site or contract'
        s.save()


class Migration(migrations.Migration):
    dependencies = [('siteconfig', '0003_hiring_flags')]
    operations = [migrations.RunPython(refresh, migrations.RunPython.noop)]

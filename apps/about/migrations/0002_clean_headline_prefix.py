from django.db import migrations


def strip_prefix(apps, schema_editor):
    Profile = apps.get_model('about', 'Profile')
    for p in Profile.objects.filter(headline__istartswith='headline:'):
        p.headline = p.headline.split(':', 1)[1].strip()
        p.save(update_fields=['headline'])


class Migration(migrations.Migration):
    dependencies = [('about', '0001_initial')]
    operations = [migrations.RunPython(strip_prefix, migrations.RunPython.noop)]

from django.db import migrations


def strip_prefix(apps, schema_editor):
    Experience = apps.get_model('experience', 'Experience')
    for e in Experience.objects.filter(date_range__istartswith='date range:'):
        e.date_range = e.date_range.split(':', 1)[1].strip()
        e.save(update_fields=['date_range'])


class Migration(migrations.Migration):
    dependencies = [('experience', '0001_initial')]
    operations = [migrations.RunPython(strip_prefix, migrations.RunPython.noop)]

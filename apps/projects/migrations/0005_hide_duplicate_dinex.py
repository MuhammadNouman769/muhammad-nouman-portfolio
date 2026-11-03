from django.db import migrations


def hide(apps, schema_editor):
    # The older "dinex-pos" row duplicates the full "dinex" case study.
    P = apps.get_model('projects', 'Project')
    if P.objects.filter(slug='dinex', published=True).exists():
        P.objects.filter(slug='dinex-pos').update(published=False)


class Migration(migrations.Migration):
    dependencies = [('projects', '0004_project_accent_project_architecture_and_more')]
    operations = [migrations.RunPython(hide, migrations.RunPython.noop)]

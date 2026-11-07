import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = []

    operations = [
        migrations.CreateModel(
            name='Income',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(help_text='What was this for? e.g. E-commerce website for Ali', max_length=160)),
                ('client', models.CharField(blank=True, max_length=120)),
                ('source', models.CharField(choices=[('upwork', 'Upwork'), ('fiverr', 'Fiverr'), ('direct', 'Direct client'), ('xvera', 'Xvera Labs'), ('job', 'Job / salary (TheTechFury)'), ('freelance', 'Other freelance'), ('other', 'Other')], default='direct', help_text='Where the money comes from.', max_length=12)),
                ('total_amount', models.DecimalField(decimal_places=0, help_text='Total agreed amount (Rs).', max_digits=12)),
                ('received', models.DecimalField(decimal_places=0, default=0, help_text='How much has been paid to you so far (Rs).', max_digits=12)),
                ('date', models.DateField(default=django.utils.timezone.localdate, help_text='Deal / invoice date.')),
                ('due_date', models.DateField(blank=True, help_text='When the remaining balance is expected.', null=True)),
                ('note', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={'ordering': ['-date', '-id']},
        ),
        migrations.CreateModel(
            name='Expense',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(help_text='What did you pay for?', max_length=160)),
                ('category', models.CharField(choices=[('hosting', 'Hosting & servers'), ('tools', 'Software & tools'), ('salary', 'Salaries & freelancers'), ('ads', 'Marketing & ads'), ('office', 'Office & rent'), ('utilities', 'Internet & utilities'), ('learning', 'Courses & learning'), ('food', 'Food & daily'), ('hardware', 'Hardware'), ('other', 'Other')], default='other', max_length=12)),
                ('spent_at', models.CharField(blank=True, help_text='Shop, vendor or person. e.g. Hostinger, Google Ads', max_length=120, verbose_name='Where / paid to')),
                ('amount', models.DecimalField(decimal_places=0, max_digits=12)),
                ('date', models.DateField(default=django.utils.timezone.localdate)),
                ('note', models.TextField(blank=True, help_text='Any detail: invoice no., reason, project it belongs to.')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={'ordering': ['-date', '-id']},
        ),
    ]

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("siteconfig", "0004_refresh_copy")]

    operations = [
        migrations.CreateModel(
            name="Banner",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("placement", models.CharField(choices=[("home", "Home page (moving slider)"), ("about", "About page"), ("projects", "Projects page"), ("blog", "Blog page"), ("experience", "Experience page"), ("skills", "Skills page"), ("services", "Services page"), ("contact", "Contact page"), ("privacy", "Privacy page")], default="home", max_length=20)),
                ("title", models.CharField(blank=True, help_text="Headline on a home slider slide. Also used as the image description.", max_length=90)),
                ("text", models.CharField(blank=True, help_text="One or two short sentences under the headline (home slider only).", max_length=200)),
                ("image", models.ImageField(help_text="Wide picture, about 1600 x 1000 px (16:10). Max 5 MB.", upload_to="banners/")),
                ("button_text", models.CharField(blank=True, help_text='Optional, e.g. "Read case study".', max_length=30)),
                ("button_url", models.CharField(blank=True, help_text="Optional page or link, e.g. /projects/btr-mall/ or https://...", max_length=300)),
                ("accent", models.CharField(default="#3452e8", help_text="Hex colour for the glow behind this banner, e.g. #3452e8.", max_length=7)),
                ("active", models.BooleanField(default=True, help_text="Untick to hide this banner without deleting it.")),
                ("order", models.PositiveIntegerField(default=0)),
            ],
            options={"ordering": ["placement", "order", "id"]},
        ),
    ]

"""Adds 12 clearly marked dummy books (with small real PDFs) so the Books section can be previewed.

    python manage.py seed_books            # create / refresh the dummy books
    python manage.py seed_books --remove   # delete them again (your own books are never touched)
"""
import io
import random
from datetime import date, timedelta

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer

from django.utils import timezone

from apps.books.models import Book, BookDownload

DUMMY = [
    # slug, title, subtitle, summary, language, pages, written_on, accent, featured
    ('dummy-django-interview-prep', 'Django Interview Prep', 'Roman Urdu mein ORM, views aur DRF',
     'Django interviews mein puche jane wale sawalat, saaf Roman Urdu mein jawab ke sath.', 'rur', 120, date(2026, 10, 28), '#1f7a5a', True),
    ('dummy-drf-zero-to-hero', 'DRF Zero to Hero', 'Serializers se production APIs tak',
     'Django REST Framework step by step: serializers, viewsets, permissions aur testing.', 'en', 96, date(2026, 10, 10), '#15803d', False),
    ('dummy-python-basics-urdu', 'Python Basics', 'Pehli dafa programming seekhne walon ke liye',
     'Variables se OOP tak, chhote chhote examples ke sath Python ki buniyad.', 'rur', 84, date(2026, 9, 21), '#047857', False),
    ('dummy-system-design-notes', 'System Design Notes', 'Backend engineers ke liye',
     'Caching, queues, database scaling aur tradeoffs: ek practical notebook.', 'en', 140, date(2026, 9, 2), '#3f6212', False),
    ('dummy-postgres-in-practice', 'PostgreSQL in Practice', 'Indexes, queries aur migrations',
     'Slow queries ko samajhna aur theek karna, real Django projects ki misalon se.', 'en', 72, date(2026, 8, 15), '#166534', False),
    ('dummy-fastapi-quickstart', 'FastAPI Quickstart', 'Async APIs ek hafte mein',
     'FastAPI, Pydantic aur async database access ka tez raftar introduction.', 'en', 64, date(2026, 7, 30), '#2f855a', False),
    ('dummy-git-for-teams', 'Git for Teams', 'Branching, reviews aur clean history',
     'Team ke sath kaam karne ka Git workflow: PRs, rebase aur conflict resolution.', 'rur', 48, date(2026, 7, 4), '#4d7c0f', False),
    ('dummy-clean-code-python', 'Clean Code in Python', 'Padhne mein asaan code likhna',
     'Naming, functions, tests aur refactoring: code ko aise likhein ke kal bhi samajh aaye.', 'en', 110, date(2026, 6, 12), '#065f46', False),
    ('dummy-freelancing-guide', 'Freelancing Guide', 'Pehla client aur pehli invoice',
     'Developers ke liye freelancing: profile, proposals, pricing aur client communication.', 'rur', 56, date(2026, 5, 20), '#14532d', False),
    ('dummy-docker-for-django', 'Docker for Django', 'Local se server tak',
     'Dockerfile, compose, gunicorn aur nginx ke sath Django ko deploy karna.', 'en', 80, date(2026, 4, 18), '#276749', False),
    ('dummy-writing-for-devs', 'Writing for Developers', 'Technical likhai ka hunar',
     'Blog, docs aur books likhne ke asan usool, taake readers ko baat jaldi samajh aaye.', 'rur', 40, date(2026, 3, 9), '#0b5d3b', False),
    ('dummy-testing-django', 'Testing Django Apps', 'Confidence ke sath ship karein',
     'Unit tests, fixtures, API tests aur CI: bugs ko production se pehle pakarna.', 'en', 68, date(2026, 2, 1), '#22764f', False),
]

PURPOSE = ('Ye ek dummy (namoona) book hai jo sirf is section ko preview karne ke liye banayi gayi hai.\n\n'
           'Apni asli book dashboard se add karein, phir is dummy ko delete kar dein.')
AUDIENCE = 'Beginners jo pehli dafa ye topic seekh rahe hain\nBackend developers jo apni knowledge refresh karna chahte hain\nInterview ki tayyari karne wale students'
LEARN = 'Buniyadi concepts saaf tareeqe se\nReal projects mein istemal hone wali misalein\nAam ghaltiyan aur unse bachne ke tareeqe\nAgle qadam ke liye roadmap'
BODY = ('## Is book mein kya hai\n\nYe chapter-by-chapter guide hai. Har chapter chhota hai aur ek hi cheez sikhata hai.\n\n'
        '- Chhote examples\n- Practice sawalat\n- Summary har chapter ke aakhir mein')


def make_pdf(title, subtitle, summary):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, title=title, author='Muhammad Nouman')
    st = getSampleStyleSheet()
    story = [Spacer(1, 200), Paragraph(title, st['Title']), Paragraph(subtitle, st['Heading3']), Spacer(1, 18),
             Paragraph(summary, st['BodyText']), Spacer(1, 40), Paragraph('Sample PDF generated for preview.', st['Italic']), PageBreak()]
    for n in range(1, 4):
        story.append(Paragraph(f'Chapter {n}', st['Heading1']))
        for _ in range(4):
            story.append(Paragraph('Ye sample matn hai. Asli book upload karne par yahan aap ka apna content hoga. ' * 4, st['BodyText']))
            story.append(Spacer(1, 8))
        if n < 3:
            story.append(PageBreak())
    doc.build(story)
    return buf.getvalue()


class Command(BaseCommand):
    help = 'Create (or with --remove, delete) dummy books for previewing the Books section.'

    def add_arguments(self, parser):
        parser.add_argument('--remove', action='store_true')

    def handle(self, *args, **opts):
        slugs = [d[0] for d in DUMMY]
        if opts['remove']:
            n = 0
            for b in Book.objects.filter(slug__in=slugs):
                if b.pdf_file:
                    b.pdf_file.delete(save=False)
                b.delete()
                n += 1
            self.stdout.write(self.style.SUCCESS(f'Removed {n} dummy books.'))
            return
        created = 0
        for slug, title, sub, summary, lang, pages, written, accent, featured in DUMMY:
            book, was_new = Book.objects.update_or_create(slug=slug, defaults=dict(
                title=title, subtitle=sub, summary=summary, description=BODY, purpose=PURPOSE, audience=AUDIENCE,
                learn=LEARN, language=lang, pages=pages, written_on=written, cover_accent=accent, featured=featured,
                published=True))
            if not book.pdf_file:
                book.pdf_file.save(f'{slug}.pdf', ContentFile(make_pdf(title, sub, summary)), save=True)
            if was_new:
                self._fake_downloads(book)
            created += was_new
        self.stdout.write(self.style.SUCCESS(f'{len(DUMMY)} dummy books ready ({created} new). Delete them with: python manage.py seed_books --remove'))

    def _fake_downloads(self, book):
        """Sample download history so the dashboard Downloads page has something to show."""
        rnd = random.Random(book.slug)
        agents = [('desktop', 'Chrome', 'Windows'), ('mobile', 'Chrome', 'Android'), ('mobile', 'Safari', 'iOS'),
                  ('desktop', 'Firefox', 'Linux'), ('desktop', 'Edge', 'Windows')]
        countries = ['PK', 'PK', 'PK', 'IN', 'AE', 'GB', 'US', 'SA']
        refs = ['', '', 'google.com', 'linkedin.com', 'github.com', 'whatsapp.com']
        n = rnd.randint(3, 40)
        rows = []
        for _ in range(n):
            dev, br, os_name = rnd.choice(agents)
            when = timezone.now() - timedelta(days=rnd.randint(0, 45), hours=rnd.randint(0, 23), minutes=rnd.randint(0, 59))
            rows.append(BookDownload(book=book, created_at=when, ip=f'203.0.113.{rnd.randint(1, 250)}', country=rnd.choice(countries),
                                     device=dev, browser=br, os=os_name, referrer=rnd.choice(refs)))
        BookDownload.objects.bulk_create(rows)
        Book.objects.filter(pk=book.pk).update(download_count=n)

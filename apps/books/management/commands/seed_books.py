"""Creates sample books (cover image + a small sample PDF each) so the Books page is not empty.

Safe to run more than once: books are matched by slug and never duplicated.
    python manage.py seed_books
"""
import io
from datetime import date

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from PIL import Image, ImageDraw, ImageFont

from apps.books.models import Book

OWNER = 'Muhammad Nouman'

BOOKS = [
    dict(slug='django-in-production', title='Django in Production', subtitle='A practical handbook for shipping and running backends',
         category='Technical', language='English', pages=184, published_on=date(2025, 9, 15), accent='#14532d', featured=True,
         summary='Settings, deployment, caching, background jobs and monitoring: the checklist I use to take a Django app from laptop to production.',
         description='This handbook collects what I wish I had known before my first production Django deployment. It is organised as a series of short, practical chapters that you can read in any order.\n\nYou will find a repeatable settings layout, a Docker Compose + Nginx + Gunicorn setup, a caching strategy that does not fight you later, idempotent Celery tasks, and a monitoring baseline that catches problems before your users do.\n\nSample edition: this is placeholder text. Replace it from the dashboard with the real description.'),
    dict(slug='designing-multi-vendor-marketplaces', title='Designing Multi-Vendor Marketplaces', subtitle='Orders, payouts and tenancy without the pain',
         category='Technical', language='English', pages=142, published_on=date(2026, 3, 10), accent='#166534',
         summary='How to model orders that split across sellers, handle payouts and refunds, and keep every vendor\'s data isolated.',
         description='A focused guide to the data model and APIs behind a multi-vendor marketplace: one order, many shipments, commission rules, and refunds that reconcile.\n\nEach chapter ends with a short checklist you can apply to your own project.\n\nSample edition: placeholder text for demonstration.'),
    dict(slug='harf-e-shauq', title='Harf-e-Shauq', subtitle='Ghazals',
         category='Poetry', language='Urdu', pages=96, published_on=date(2024, 12, 5), accent='#1f6b3e',
         summary='A collection of ghazals on longing, patience and the quiet moments in between.',
         description='Harf-e-Shauq gathers ghazals written over several years, arranged in the order they were written so the reader can follow the change in voice.\n\nSample edition: placeholder text for demonstration.'),
    dict(slug='khamoshi-ke-rang', title='Khamoshi ke Rang', subtitle='Nazmain',
         category='Poetry', language='Urdu', pages=88, published_on=date(2025, 5, 20), accent='#2d6a4f',
         summary='Free-verse nazmain about silence, memory and the small colours of everyday life.',
         description='A slim volume of nazmain, each built around a single image. Short enough to read in one evening, and meant to be read again.\n\nSample edition: placeholder text for demonstration.'),
    dict(slug='dil-ki-diary', title='Dil ki Diary', subtitle='Essays and reflections',
         category='Essays', language='Urdu', pages=128, published_on=date(2023, 11, 18), accent='#7a5c14',
         summary='Personal essays on work, faith, family and learning to slow down.',
         description='Dil ki Diary is a set of short personal essays written in plain language. Each piece stands alone and can be read in about ten minutes.\n\nSample edition: placeholder text for demonstration.'),
    dict(slug='notes-from-a-developers-desk', title='Notes from a Developer\'s Desk', subtitle='Essays on building software and a career',
         category='Essays', language='English', pages=110, published_on=date(2026, 8, 2), accent='#15803d',
         summary='Short essays on code review, learning in public, estimating honestly and staying curious for the long run.',
         description='Notes from a Developer\'s Desk collects essays written between releases. They are about the human side of engineering: how teams decide, how people learn, and how small habits compound.\n\nSample edition: placeholder text for demonstration.'),
]


def _font(size):
    return ImageFont.load_default(size=size)


def _wrap(draw, text, font, width):
    lines, cur = [], ''
    for word in text.split():
        trial = f'{cur} {word}'.strip()
        if draw.textlength(trial, font=font) <= width:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def make_cover(title, subtitle, category, accent):
    w, h = 800, 1200
    r, g, b = (int(accent[i:i + 2], 16) for i in (1, 3, 5))
    img = Image.new('RGB', (w, h))
    px = img.load()
    for y in range(h):
        t = y / h
        k = 1 - 0.55 * t
        for x in range(w):
            px[x, y] = (int(r * k), int(g * k), int(b * k))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, 26, h], fill=(0, 0, 0))
    d.rectangle([26, 0, 30, h], fill=(255, 255, 255))
    d.rectangle([70, 70, w - 70, h - 70], outline=(255, 255, 255), width=3)
    d.text((110, 120), category.upper(), font=_font(34), fill=(255, 255, 255))
    y = 360
    big = _font(92)
    for line in _wrap(d, title, big, w - 260):
        d.text((110, y), line, font=big, fill=(255, 255, 255))
        y += 110
    if subtitle:
        y += 20
        sm = _font(40)
        for line in _wrap(d, subtitle, sm, w - 260):
            d.text((110, y), line, font=sm, fill=(255, 235, 220))
            y += 52
    d.line([110, h - 220, 330, h - 220], fill=(255, 255, 255), width=4)
    d.text((110, h - 190), OWNER, font=_font(46), fill=(255, 255, 255))
    out = io.BytesIO()
    img.save(out, 'JPEG', quality=88)
    return out.getvalue()


def make_pdf(title, subtitle, pages):
    from reportlab.lib.pagesizes import A5
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A5, title=title, author=OWNER, leftMargin=42, rightMargin=42, topMargin=54, bottomMargin=54)
    st = getSampleStyleSheet()
    body = ('This is a sample page generated so the Books section can be demonstrated. '
            'Replace this PDF with the real book from the dashboard (Books, then Edit, then PDF file). ') * 6
    flow = [Spacer(1, 150), Paragraph(title, st['Title']), Paragraph(subtitle or '', st['Heading3']),
            Spacer(1, 30), Paragraph(OWNER, st['Normal']), Spacer(1, 12), Paragraph('Sample edition', st['Italic']), PageBreak(),
            Paragraph('Contents', st['Heading1'])]
    flow += [Paragraph(f'Chapter {i}', st['Normal']) for i in range(1, 6)] + [PageBreak()]
    for i in range(1, 4):
        flow += [Paragraph(f'Chapter {i}', st['Heading1']), Paragraph(body, st['BodyText']), Spacer(1, 10), Paragraph(body, st['BodyText'])]
        if i < 3:
            flow.append(PageBreak())
    doc.build(flow)
    return buf.getvalue()


class Command(BaseCommand):
    help = 'Create sample books (cover + sample PDF). Existing books are left alone.'

    def handle(self, *args, **opts):
        created = 0
        for i, row in enumerate(BOOKS, start=1):
            if Book.objects.filter(slug=row['slug']).exists():
                continue
            b = Book(slug=row['slug'], title=row['title'], subtitle=row['subtitle'], summary=row['summary'],
                     description=row['description'], category=row['category'], language=row['language'],
                     pages=row['pages'], published_on=row['published_on'], cover_accent=row['accent'],
                     featured=row.get('featured', False), order=i)
            b.cover_image.save(f"{row['slug']}.jpg", ContentFile(make_cover(row['title'], row['subtitle'], row['category'], row['accent'])), save=False)
            b.pdf_file.save(f"{row['slug']}.pdf", ContentFile(make_pdf(row['title'], row['subtitle'], row['pages'])), save=False)
            b.save()
            created += 1
        self.stdout.write(self.style.SUCCESS(f'{created} sample book(s) created.'))

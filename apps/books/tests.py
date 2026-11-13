import tempfile

from django.core.files.base import ContentFile
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import Book


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class BookTests(TestCase):
    def setUp(self):
        self.book = Book.objects.create(title='Sample Book', summary='A short summary.', description='One.\n\nTwo.', category='Technical', pages=10)
        self.book.pdf_file.save('sample.pdf', ContentFile(b'%PDF-1.4\n%%EOF'), save=True)

    def test_slug_and_paragraphs(self):
        self.assertEqual(self.book.slug, 'sample-book')
        self.assertEqual(self.book.paragraphs, ['One.', 'Two.'])

    def test_pages_render(self):
        self.assertContains(self.client.get(reverse('books:index')), 'Sample Book')
        self.assertContains(self.client.get(self.book.get_absolute_url()), 'Download PDF')

    def test_download_counts(self):
        r = self.client.get(reverse('books:download', args=[self.book.slug]))
        self.assertEqual(r.status_code, 200)
        self.book.refresh_from_db()
        self.assertEqual(self.book.downloads, 1)

    def test_hidden_book_is_404(self):
        self.book.published = False
        self.book.save()
        self.assertEqual(self.client.get(self.book.get_absolute_url()).status_code, 404)


import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class DashboardBookTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        from django.conf import settings
        shutil.rmtree(settings.MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        user = get_user_model().objects.create_user('admin', password='pw', is_staff=True, is_superuser=True)
        self.client.force_login(user)

    def _data(self, **kw):
        d = {'title': 'My New Book', 'slug': '', 'subtitle': '', 'summary': 'Short text.', 'description': 'Long text.\n\nMore.',
             'category': 'Poetry', 'language': 'Urdu', 'pages': '50', 'published_on': '2026-01-05', 'cover_accent': '#14532d',
             'published': 'on'}
        d.update(kw)
        return d

    def test_list_and_form_open(self):
        self.assertEqual(self.client.get(reverse('dashboard:resource_list', args=['books'])).status_code, 200)
        r = self.client.get(reverse('dashboard:resource_new', args=['books']))
        self.assertEqual(r.status_code, 200)
        for name in ('title', 'summary', 'description', 'cover_image', 'pdf_file', 'published_on'):
            self.assertContains(r, f'name="{name}"')

    def test_add_book_with_pdf(self):
        pdf = SimpleUploadedFile('book.pdf', b'%PDF-1.4\n1 0 obj\n%%EOF', content_type='application/pdf')
        r = self.client.post(reverse('dashboard:resource_new', args=['books']), self._data(pdf_file=pdf))
        self.assertIn(r.status_code, (302, 303), getattr(r, 'context', None) and r.context['form'].errors)
        b = Book.objects.get(title='My New Book')
        self.assertTrue(b.pdf_file.name.endswith('.pdf'))
        self.assertContains(self.client.get(reverse('books:index')), 'My New Book')

    def test_rejects_fake_pdf(self):
        bad = SimpleUploadedFile('book.pdf', b'not a pdf at all', content_type='application/pdf')
        r = self.client.post(reverse('dashboard:resource_new', args=['books']), self._data(pdf_file=bad))
        self.assertEqual(r.status_code, 200)
        self.assertFalse(Book.objects.filter(title='My New Book').exists())

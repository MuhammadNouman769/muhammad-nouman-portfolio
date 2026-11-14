import shutil
import tempfile
from datetime import date

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import Book, BookDownload

User = get_user_model()
PDF = b'%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n'
TMP = tempfile.mkdtemp()


def make(title='Alpha Book', **kw):
    kw.setdefault('summary', 'A small summary.')
    return Book.objects.create(title=title, **kw)


@override_settings(MEDIA_ROOT=TMP)
class BookModelTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TMP, ignore_errors=True)

    def test_slug_unique_and_lists(self):
        a, b = make('Same Title'), make('Same Title')
        self.assertEqual(a.slug, 'same-title')
        self.assertEqual(b.slug, 'same-title-2')
        b.audience = '- Beginners\n\n* Writers\nStudents'
        b.learn = 'One\nTwo'
        self.assertEqual(b.audience_list, ['Beginners', 'Writers', 'Students'])
        self.assertEqual(b.learn_list, ['One', 'Two'])

    def test_ordering_featured_then_newest(self):
        old = make('Old', written_on=date(2020, 1, 1))
        new = make('New', written_on=date(2025, 1, 1))
        feat = make('Feat', written_on=date(2019, 1, 1), featured=True)
        self.assertEqual(list(Book.objects.all()), [feat, new, old])


@override_settings(MEDIA_ROOT=TMP)
class BookDashboardTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user('boss', 'b@example.com', 'pw12345!x', is_staff=True)
        self.client.login(username='boss', password='pw12345!x')
        self.new = reverse('dashboard:resource_new', args=['books'])

    def payload(self, **over):
        d = {'title': 'My Django Book', 'slug': '', 'subtitle': '', 'summary': 'Short text.', 'description': '## Hi\n\nBody.',
             'author': 'Muhammad Nouman', 'purpose': 'To teach.', 'audience': 'Beginners\nBackend devs', 'learn': 'ORM\nDRF', 'language': 'rur',
             'pages': '120', 'written_on': '2026-03-05', 'cover_accent': '#3452e8', 'meta_description': '',
             'published': 'on'}
        d.update(over)
        return d

    def test_list_and_form_render(self):
        self.assertContains(self.client.get(reverse('dashboard:resource_list', args=['books'])), 'Books')
        r = self.client.get(self.new)
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'multipart/form-data')
        self.assertContains(r, 'name="pdf_file"')

    def test_create_with_pdf(self):
        pdf = SimpleUploadedFile('book.pdf', PDF, content_type='application/pdf')
        r = self.client.post(self.new, self.payload(pdf_file=pdf))
        self.assertEqual(r.status_code, 302)
        b = Book.objects.get()
        self.assertEqual(b.slug, 'my-django-book')
        self.assertTrue(b.has_pdf)
        self.assertEqual(b.written_on, date(2026, 3, 5))
        self.assertEqual(b.get_language_display(), 'Roman Urdu')
        self.assertContains(self.client.get(reverse('dashboard:resource_list', args=['books'])), 'My Django Book')

    def test_rejects_fake_pdf_and_wrong_extension(self):
        fake = SimpleUploadedFile('book.pdf', b'not a pdf at all', content_type='application/pdf')
        self.assertEqual(self.client.post(self.new, self.payload(pdf_file=fake)).status_code, 200)
        exe = SimpleUploadedFile('book.exe', PDF)
        self.assertEqual(self.client.post(self.new, self.payload(pdf_file=exe)).status_code, 200)
        self.assertEqual(Book.objects.count(), 0)

    def test_edit_keeps_existing_pdf_and_toggle_and_delete(self):
        pdf = SimpleUploadedFile('book.pdf', PDF, content_type='application/pdf')
        self.client.post(self.new, self.payload(pdf_file=pdf))
        b = Book.objects.get()
        edit = reverse('dashboard:resource_edit', args=['books', b.pk])
        self.assertEqual(self.client.post(edit, self.payload(title='Renamed', slug=b.slug)).status_code, 302)
        b.refresh_from_db()
        self.assertEqual(b.title, 'Renamed')
        self.assertTrue(b.has_pdf)                       # editing without re-uploading must not drop the PDF
        t = reverse('dashboard:resource_toggle', args=['books', b.pk, 'featured'])
        self.client.post(t)
        b.refresh_from_db()
        self.assertTrue(b.featured)
        self.client.post(reverse('dashboard:resource_delete', args=['books', b.pk]))
        self.assertEqual(Book.objects.count(), 0)

    def test_requires_staff(self):
        self.client.logout()
        self.assertEqual(self.client.get(self.new).status_code, 302)


@override_settings(MEDIA_ROOT=TMP)
class BookPublicTests(TestCase):
    def setUp(self):
        self.pdf = SimpleUploadedFile('x.pdf', PDF, content_type='application/pdf')
        self.book = make('Public Book', purpose='Why I wrote it.', audience='Beginners\nWriters', learn='ORM\nDRF',
                         description='## About\n\nSome text.', pages=88, pdf_file=self.pdf)
        make('Draft Book', published=False)

    def test_index_lists_only_published_with_header_link(self):
        r = self.client.get(reverse('books:index'))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Public Book')
        self.assertNotContains(r, 'Draft Book')
        self.assertContains(r, 'href="/books/"')                 # header link
        self.assertContains(r, 'data-lamp')

    def test_pagination_nine_per_page(self):
        for i in range(11):
            make(f'Filler {i:02d}', written_on=date(2024, 1, 1 + i))
        p1 = self.client.get(reverse('books:index'))
        self.assertEqual(len(p1.context['books']), 9)
        self.assertContains(p1, 'aria-label="Books pages"')
        p2 = self.client.get(reverse('books:index') + '?page=2')
        self.assertEqual(len(p2.context['books']), 3)           # 12 published in total
        self.assertEqual(self.client.get(reverse('books:index') + '?page=999').status_code, 200)

    def test_no_pagination_for_nine_or_fewer(self):
        self.assertNotContains(self.client.get(reverse('books:index')), 'Books pages')

    def test_detail_sections(self):
        r = self.client.get(self.book.get_absolute_url())
        for text in ('Purpose of this book', 'Why I wrote it.', 'Who will benefit', 'Writers', 'What you will learn',
                     'Download PDF', 'Written on', '88', '"@type":"Book"'):
            self.assertContains(r, text)

    def test_draft_hidden_but_staff_preview(self):
        draft = Book.objects.get(title='Draft Book')
        self.assertEqual(self.client.get(draft.get_absolute_url()).status_code, 404)
        User.objects.create_user('s', 's@example.com', 'pw12345!x', is_staff=True)
        self.client.login(username='s', password='pw12345!x')
        self.assertContains(self.client.get(draft.get_absolute_url()), 'Draft preview')

    def test_download_counts_and_is_attachment(self):
        r = self.client.get(self.book.get_download_url(), HTTP_USER_AGENT=BROWSER)   # no user-agent counts as a bot
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r['Content-Type'], 'application/pdf')
        self.assertIn('attachment', r['Content-Disposition'])
        self.assertEqual(b''.join(r.streaming_content), PDF)
        self.book.refresh_from_db()
        self.assertEqual(self.book.download_count, 1)

    def test_download_404_without_pdf_or_for_draft(self):
        nopdf = make('No Pdf')
        self.assertEqual(self.client.get(nopdf.get_download_url()).status_code, 404)
        self.assertContains(self.client.get(nopdf.get_absolute_url()), 'PDF coming soon')
        draft = Book.objects.get(title='Draft Book')
        self.assertEqual(self.client.get(draft.get_download_url()).status_code, 404)

    def test_theme_applied_on_list_and_detail(self):
        self.assertContains(self.client.get(reverse('books:index')), 'bk-theme bk-band')
        self.assertContains(self.client.get(self.book.get_absolute_url()), 'book-page bk-theme')
        css = open('static/css/books.css').read()
        for v in ('--bk-bg', '--bk-accent', '[data-theme="dark"] .bk-theme'):
            self.assertIn(v, css)

    def test_no_hover_rules_on_cards(self):
        css = open('static/css/books.css').read()
        self.assertNotIn('translateY', css)

    def test_sitemap_and_robots(self):
        sm = self.client.get('/sitemap.xml').content.decode()
        self.assertIn('/books/', sm)
        self.assertIn('/books/public-book/', sm)
        self.assertNotIn('draft-book', sm)
        self.assertIn('Disallow: /books/*/download/', self.client.get('/robots.txt').content.decode())


@override_settings(MEDIA_ROOT=TMP)
class SeedBooksTests(TestCase):
    def test_seed_is_idempotent_and_removable(self):
        from django.core.management import call_command
        mine = make('My Real Book')
        call_command('seed_books', verbosity=0)
        call_command('seed_books', verbosity=0)
        self.assertEqual(Book.objects.count(), 13)
        self.assertTrue(BookDownload.objects.filter(book__slug='dummy-django-interview-prep').exists())
        first = Book.objects.get(slug='dummy-django-interview-prep')
        self.assertTrue(first.pdf_file.name.endswith('.pdf'))
        r = self.client.get(reverse('books:index'))
        self.assertEqual(len(r.context['books']), 9)             # 13 books -> 9 + 4 on page 2
        self.assertEqual(len(self.client.get(reverse('books:index') + '?page=2').context['books']), 4)
        dl = self.client.get(first.get_download_url())
        self.assertTrue(b''.join(dl.streaming_content).startswith(b'%PDF-'))
        call_command('seed_books', '--remove', verbosity=0)
        self.assertEqual(list(Book.objects.all()), [mine])      # only the real book is left


BROWSER = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36'


@override_settings(MEDIA_ROOT=TMP)
class DownloadLogTests(TestCase):
    def setUp(self):
        self.book = make('Logged', pdf_file=SimpleUploadedFile('x.pdf', PDF, content_type='application/pdf'))

    def test_human_download_is_logged_with_details(self):
        r = self.client.get(self.book.get_download_url(), HTTP_USER_AGENT=BROWSER, HTTP_REFERER='https://google.com/search')
        self.assertEqual(r.status_code, 200)
        d = BookDownload.objects.get()
        self.assertEqual((d.book, d.device, d.browser), (self.book, 'desktop', 'Chrome'))
        self.assertTrue(d.ip)
        self.book.refresh_from_db()
        self.assertEqual(self.book.download_count, 1)

    def test_bots_and_staff_are_not_logged_but_still_served(self):
        r = self.client.get(self.book.get_download_url(), HTTP_USER_AGENT='Googlebot/2.1')
        self.assertEqual(r.status_code, 200)
        User.objects.create_user('s', 's@example.com', 'pw12345!x', is_staff=True)
        self.client.login(username='s', password='pw12345!x')
        self.client.get(self.book.get_download_url(), HTTP_USER_AGENT=BROWSER)
        self.assertEqual(BookDownload.objects.count(), 0)
        self.book.refresh_from_db()
        self.assertEqual(self.book.download_count, 0)

    def test_deleting_book_removes_its_log(self):
        self.client.get(self.book.get_download_url(), HTTP_USER_AGENT=BROWSER)
        self.book.delete()
        self.assertEqual(BookDownload.objects.count(), 0)


@override_settings(MEDIA_ROOT=TMP)
class DownloadDashboardTests(TestCase):
    def setUp(self):
        User.objects.create_user('boss', 'b@example.com', 'pw12345!x', is_staff=True)
        self.client.login(username='boss', password='pw12345!x')
        self.a = make('Book A', pdf_file=SimpleUploadedFile('a.pdf', PDF, content_type='application/pdf'))
        self.b = make('Book B')
        from django.utils import timezone
        from datetime import timedelta
        for i in range(3):
            BookDownload.objects.create(book=self.a, country='PK', device='mobile', browser='Chrome', os='Android', ip='1.2.3.4')
        BookDownload.objects.create(book=self.a, created_at=timezone.now() - timedelta(days=60), country='US', device='desktop', browser='Edge')
        BookDownload.objects.create(book=self.b, referrer='google.com')

    def test_overview_shows_counts_per_book(self):
        r = self.client.get(reverse('dashboard:book_downloads'))
        self.assertEqual(r.status_code, 200)
        rows = {x['book'].title: x for x in r.context['rows']}
        self.assertEqual((rows['Book A']['n'], rows['Book A']['total']), (3, 4))   # 30-day window vs all time
        self.assertEqual(rows['Book B']['n'], 1)
        self.assertEqual(r.context['rows'][0]['book'], self.a)                    # most downloaded first
        self.assertEqual(r.context['total']['all'], 5)
        self.assertContains(r, 'Book downloads')

    def test_all_time_range(self):
        r = self.client.get(reverse('dashboard:book_downloads') + '?range=all')
        self.assertEqual({x['book'].title: x['n'] for x in r.context['rows']}['Book A'], 4)

    def test_book_detail_page(self):
        r = self.client.get(reverse('dashboard:book_download_detail', args=[self.a.pk]) + '?range=all')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.context['total']['all'], 4)
        self.assertEqual(r.context['in_range'], 4)
        self.assertEqual(len(r.context['daily']), 14)
        self.assertContains(r, 'Book A')
        self.assertEqual(self.client.get(reverse('dashboard:book_download_detail', args=[9999])).status_code, 404)

    def test_csv_export(self):
        r = self.client.get(reverse('dashboard:book_downloads_export') + f'?book={self.a.pk}&range=all')
        lines = r.content.decode().strip().splitlines()
        self.assertEqual(len(lines), 5)                                           # header + 4 rows
        self.assertTrue(all('Book A' in ln for ln in lines[1:]))

    def test_sidebar_link_and_staff_only(self):
        self.assertContains(self.client.get(reverse('dashboard:overview')), reverse('dashboard:book_downloads'))
        self.client.logout()
        self.assertEqual(self.client.get(reverse('dashboard:book_downloads')).status_code, 302)


@override_settings(MEDIA_ROOT=TMP)
class ReadOnlineAndAuthorTests(TestCase):
    def setUp(self):
        self.book = make('Readable', author='Aslam Khan', pdf_file=SimpleUploadedFile('r.pdf', PDF, content_type='application/pdf'))

    def test_detail_has_read_online_and_author(self):
        r = self.client.get(self.book.get_absolute_url())
        self.assertContains(r, 'Read online')
        self.assertContains(r, self.book.get_read_url())
        self.assertContains(r, 'Aslam Khan')
        self.assertContains(r, '"name":"Aslam Khan"')               # structured data names the real author

    def test_author_falls_back_to_site_name(self):
        other = make('Anon')
        self.assertContains(self.client.get(other.get_absolute_url()), 'Muhammad Nouman')
        self.assertContains(self.client.get(reverse('books:index')), 'Aslam Khan')

    def test_reader_page_embeds_inline_pdf_without_counting(self):
        r = self.client.get(self.book.get_read_url(), HTTP_USER_AGENT=BROWSER)
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, f'<iframe class="bk-reader" src="{self.book.get_file_url()}')
        self.assertContains(r, 'noindex')
        self.assertContains(r, 'Download PDF')
        self.assertEqual(BookDownload.objects.count(), 0)

    def test_inline_file_can_be_framed_by_our_own_site_only(self):
        r = self.client.get(self.book.get_file_url(), HTTP_USER_AGENT=BROWSER)
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r['Content-Disposition'].startswith('inline'))
        self.assertEqual(r['X-Frame-Options'], 'SAMEORIGIN')
        self.assertEqual(b''.join(r.streaming_content), PDF)
        self.assertEqual(BookDownload.objects.count(), 0)

    def test_no_pdf_and_drafts(self):
        nopdf = make('Nopdf')
        self.assertEqual(self.client.get(nopdf.get_read_url()).status_code, 404)
        self.assertEqual(self.client.get(nopdf.get_file_url()).status_code, 404)
        self.assertNotContains(self.client.get(nopdf.get_absolute_url()), 'Read online')
        draft = make('Drafty', published=False, pdf_file=SimpleUploadedFile('d.pdf', PDF))
        self.assertEqual(self.client.get(draft.get_read_url()).status_code, 404)
        self.assertEqual(self.client.get(draft.get_file_url()).status_code, 404)

    def test_robots_blocks_reader_urls(self):
        robots = self.client.get('/robots.txt').content.decode()
        self.assertIn('Disallow: /books/*/read/', robots)
        self.assertIn('Disallow: /books/*/file/', robots)

    def test_old_blue_default_moves_to_green(self):
        from importlib import import_module
        mig = import_module('apps.books.migrations.0003_book_author_alter_book_cover_accent')
        old = make('Old Blue', cover_accent='#3452e8')
        keep = make('Custom', cover_accent='#a1b2c3')
        from django.apps import apps as real_apps
        mig.blue_to_green(real_apps, None)
        old.refresh_from_db(); keep.refresh_from_db()
        self.assertEqual((old.cover_accent, keep.cover_accent), ('#1f7a5a', '#a1b2c3'))
        self.assertEqual(Book._meta.get_field('cover_accent').default, '#1f7a5a')


class GreenThemeTests(TestCase):
    def setUp(self):
        self.book = make('Green Book')

    def test_every_books_page_uses_green_class(self):
        for url in (reverse('books:index'), self.book.get_absolute_url()):
            self.assertContains(self.client.get(url), '<body class="bk-green">')
        pdf = SimpleUploadedFile('g.pdf', PDF)
        with override_settings(MEDIA_ROOT=TMP):
            b = make('Has Pdf', pdf_file=pdf)
            self.assertContains(self.client.get(b.get_read_url()), '<body class="bk-green">')

    def test_books_css_has_no_blue_or_purple(self):
        import re
        css = open('static/css/books.css').read()
        for h in re.findall(r'#([0-9a-fA-F]{6})\b', css):
            r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
            self.assertFalse(b > g + 10 and b > r + 10, f'#{h} looks blue/purple')      # blue channel must not lead
            self.assertFalse(b > g + 10 and r > g + 10, f'#{h} looks purple/pink')
        words = css.lower().replace('blue/purple', '').replace('blue or purple', '')
        for word in ('blue', 'violet', 'purple', 'indigo'):
            self.assertNotIn(word, words)

    def test_green_overrides_present(self):
        css = open('static/css/books.css').read()
        for needle in (':root:has(body.bk-green)', '[data-theme="dark"]:has(body.bk-green)', '#shE stop', '#nlg stop', '#rbTeal stop', '.bk-green .ft ', '.bk-green .bot-panel header', '.bk-green .dd-menu '):
            self.assertIn(needle, css)
        self.assertNotIn('ph-blog', open('templates/books/index.html').read())

    def test_seed_colours_and_default_are_greens(self):
        from apps.books.management.commands.seed_books import DUMMY
        for row in DUMMY:
            h = row[7].lstrip('#')
            r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
            self.assertTrue(g > b and g >= r - 5, f'{row[7]} is not green')
        self.assertEqual(Book._meta.get_field('cover_accent').default, '#1f7a5a')


class FourPerRowTests(TestCase):
    def test_four_columns_on_desktop_and_fewer_on_small_screens(self):
        css = open('static/css/books.css').read()
        self.assertIn('.book-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr))', css)
        self.assertIn('max-width: 1100px) { .book-grid { grid-template-columns: repeat(3', css)
        self.assertIn('max-width: 820px) { .book-grid { grid-template-columns: repeat(2', css)
        self.assertIn('max-width: 560px) { .book-grid { grid-template-columns: minmax(0, 1fr)', css)
        self.assertIn('#books.wrap { --wrap: 1240px; }', css)

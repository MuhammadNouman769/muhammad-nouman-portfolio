import json

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.analytics.models import PageView, Visitor
from apps.contact.models import ContactMessage
from apps.projects.models import Project
from apps.skills.models import SkillCategory

User = get_user_model()
BROWSER = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36'


class PublicSiteTests(TestCase):
    def setUp(self):
        cache.clear()
        self.p = Project.objects.create(title='Alpha — Test Platform', summary='A summary.', status='live', order=1)
        Project.objects.create(title='Hidden — Draft', summary='x', published=False, order=2)

    def test_pages_render(self):
        for name in ('home:home', 'about:about', 'experience:experience', 'projects:projects', 'services:services',
                     'skills:skills', 'contact:contact', 'privacy'):
            r = self.client.get(reverse(name), HTTP_USER_AGENT=BROWSER)
            self.assertEqual(r.status_code, 200, name)
            self.assertContains(r, 'data-lamp')            # every banner carries the lamp

    def test_project_detail_and_drafts(self):
        self.assertContains(self.client.get(self.p.get_absolute_url()), 'Test Platform')
        self.assertEqual(self.client.get(reverse('projects:detail', args=['hidden-draft'])).status_code, 404)
        self.assertNotContains(self.client.get(reverse('projects:projects')), 'Hidden')

    def test_seo_endpoints(self):
        sm = self.client.get('/sitemap.xml').content.decode()
        self.assertIn('/projects/alpha-test-platform/', sm)
        self.assertNotIn('hidden-draft', sm)
        robots = self.client.get('/robots.txt').content.decode()
        self.assertIn('Disallow: /dashboard/', robots)
        self.assertIn('Sitemap:', robots)
        home = self.client.get('/').content.decode()
        self.assertIn('rel="canonical"', home)
        self.assertIn('application/ld+json', home)
        self.assertEqual(self.client.get('/does-not-exist/').status_code, 404)

    def test_contact_form_flow(self):
        url = reverse('contact:contact')
        bad = self.client.post(url, {'name': 'A', 'email': 'nope', 'message': 'hi'})
        self.assertEqual(bad.status_code, 200)
        self.assertEqual(ContactMessage.objects.count(), 0)
        ok = {'name': 'Sara', 'email': 'sara@example.com', 'subject': 'Hello', 'message': 'I need a marketplace built.'}
        self.assertEqual(self.client.post(url, ok).status_code, 302)
        self.assertEqual(ContactMessage.objects.count(), 1)
        self.client.post(url, {**ok, 'website': 'http://spam'})       # honeypot
        self.assertEqual(ContactMessage.objects.count(), 1)


class AnalyticsTests(TestCase):
    def test_human_visit_is_recorded_once_per_load(self):
        self.client.get('/', HTTP_USER_AGENT=BROWSER, HTTP_REFERER='https://www.google.com/search?q=x')
        self.client.get('/projects/', HTTP_USER_AGENT=BROWSER)
        self.assertEqual(Visitor.objects.count(), 1)
        v = Visitor.objects.get()
        self.assertEqual((v.browser, v.os, v.device, v.is_bot), ('Chrome', 'Windows', 'desktop', False))
        self.assertEqual(v.pageviews, 2)
        self.assertEqual(PageView.objects.first().path, '/projects/')
        self.assertEqual(PageView.objects.get(path='/').referrer_domain, 'google.com')

    def test_bots_flagged_and_assets_ignored(self):
        self.client.get('/', HTTP_USER_AGENT='Mozilla/5.0 (compatible; Googlebot/2.1)')
        self.assertTrue(Visitor.objects.get().is_bot)
        before = PageView.objects.count()
        self.client.get('/robots.txt'); self.client.get('/sitemap.xml'); self.client.get('/health/')
        self.assertEqual(PageView.objects.count(), before)

    def test_staff_not_tracked(self):
        User.objects.create_user('s', password='x-Pass-123456', is_staff=True)
        self.client.login(username='s', password='x-Pass-123456')
        self.client.get('/', HTTP_USER_AGENT=BROWSER)
        self.assertEqual(PageView.objects.count(), 0)

    @override_settings(ANALYTICS_ANONYMIZE_IP=True)
    def test_ip_anonymised(self):
        self.client.get('/', HTTP_USER_AGENT=BROWSER, REMOTE_ADDR='203.0.113.77')
        self.assertEqual(Visitor.objects.get().ip, '203.0.113.0')


class DashboardTests(TestCase):
    def setUp(self):
        cache.clear()
        self.staff = User.objects.create_user('boss', password='Correct-Horse-9', is_staff=True, is_superuser=True)
        self.client.login(username='boss', password='Correct-Horse-9')

    def test_anonymous_redirected_and_login_throttled(self):
        self.client.logout()
        r = self.client.get('/dashboard/')
        self.assertEqual(r.status_code, 302); self.assertIn('/dashboard/login/', r['Location'])
        for _ in range(8):
            self.client.post('/dashboard/login/', {'username': 'boss', 'password': 'wrong'})
        r = self.client.post('/dashboard/login/', {'username': 'boss', 'password': 'Correct-Horse-9'})
        self.assertContains(r, 'Too many failed attempts')

    def test_non_staff_blocked(self):
        self.client.logout()
        User.objects.create_user('guest', password='Guest-Pass-1234')
        self.client.login(username='guest', password='Guest-Pass-1234')
        self.assertEqual(self.client.get('/dashboard/').status_code, 302)

    def test_every_dashboard_screen_loads(self):
        for url in ('/dashboard/', '/dashboard/?range=7', '/dashboard/visitors/', '/dashboard/messages/',
                    '/dashboard/site-settings/', '/dashboard/about-text/', '/dashboard/account/',
                    '/dashboard/content/projects/', '/dashboard/content/projects/new/', '/dashboard/content/skills/new/',
                    '/dashboard/content/experience/new/', '/dashboard/content/services/new/',
                    '/dashboard/content/education/new/', '/dashboard/visitors/export.csv'):
            self.assertEqual(self.client.get(url).status_code, 200, url)

    def test_project_crud_with_inline_rows(self):
        data = {
            'title': 'New Thing — Platform', 'slug': '', 'summary': 'It does things.', 'body': '', 'role': '', 'year': '2026',
            'status': 'live', 'github_url': '', 'live_url': '', 'featured': 'on', 'published': 'on',
            'tags-TOTAL_FORMS': '2', 'tags-INITIAL_FORMS': '0', 'tags-MIN_NUM_FORMS': '0', 'tags-MAX_NUM_FORMS': '1000',
            'tags-0-name': 'Django', 'tags-1-name': 'Redis',
            'features-TOTAL_FORMS': '1', 'features-INITIAL_FORMS': '0', 'features-MIN_NUM_FORMS': '0', 'features-MAX_NUM_FORMS': '1000',
            'features-0-text': 'Fast', 'features-0-order': '1',
        }
        r = self.client.post('/dashboard/content/projects/new/', data)
        self.assertEqual(r.status_code, 302, getattr(r, 'context', None) and r.context['form'].errors)
        p = Project.objects.get(title__startswith='New Thing')
        self.assertEqual(p.slug, 'new-thing-platform')
        self.assertEqual([t.name for t in p.tags.all()], ['Django', 'Redis'])
        self.assertEqual(self.client.get(p.get_absolute_url()).status_code, 200)

        # toggle publish hides it from the public site
        self.client.post(f'/dashboard/content/projects/{p.pk}/toggle/published/', HTTP_X_REQUESTED_WITH='fetch')
        self.assertEqual(self.client.get(p.get_absolute_url()).status_code, 404)

        # reorder
        q = Project.objects.create(title='Second', summary='s')
        r = self.client.post('/dashboard/content/projects/reorder/', json.dumps({'ids': [q.pk, p.pk]}), content_type='application/json')
        self.assertEqual(r.json(), {'ok': True})
        self.assertEqual(list(Project.objects.values_list('pk', flat=True)), [q.pk, p.pk])

        # delete needs POST
        self.assertEqual(self.client.get(f'/dashboard/content/projects/{p.pk}/delete/').status_code, 405)
        self.client.post(f'/dashboard/content/projects/{p.pk}/delete/')
        self.assertFalse(Project.objects.filter(pk=p.pk).exists())

    def test_skill_group_and_site_settings(self):
        r = self.client.post('/dashboard/content/skills/new/', {
            'name': 'Cloud', 'skills-TOTAL_FORMS': '1', 'skills-INITIAL_FORMS': '0', 'skills-MIN_NUM_FORMS': '0',
            'skills-MAX_NUM_FORMS': '1000', 'skills-0-name': 'AWS', 'skills-0-order': '1'})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(SkillCategory.objects.get(name='Cloud').skills.get().name, 'AWS')
        from apps.siteconfig.models import SiteSettings
        s = SiteSettings.load()
        form = {f: getattr(s, f) for f in ('owner_name', 'brand_short', 'role_title', 'company_name', 'company_role',
                'hero_heading', 'hero_text', 'availability_text', 'email', 'phone', 'whatsapp', 'location', 'github',
                'linkedin', 'x_twitter', 'meta_title', 'meta_description', 'keywords', 'google_site_verification', 'bing_site_verification')}
        form.update(hero_heading='A brand new headline.', available='on')
        self.assertEqual(self.client.post('/dashboard/site-settings/', form).status_code, 302)
        self.assertContains(self.client.get('/'), 'A brand new headline.')

    def test_inbox_flow_and_csv_safety(self):
        m = ContactMessage.objects.create(name='X', email='x@example.com', subject='Hi', message='Hello there friend')
        self.assertContains(self.client.get('/dashboard/messages/'), 'Hello there')
        self.client.get(f'/dashboard/messages/{m.pk}/')
        m.refresh_from_db(); self.assertTrue(m.is_read)
        self.client.post(f'/dashboard/messages/{m.pk}/star/')
        m.refresh_from_db(); self.assertTrue(m.is_starred)
        self.client.post(f'/dashboard/messages/{m.pk}/delete/')
        self.assertEqual(ContactMessage.objects.count(), 0)
        Visitor.objects.create(uid='a' * 32, last_seen=self.staff.date_joined, first_referrer='=cmd()', device='desktop')
        csv = self.client.get('/dashboard/visitors/export.csv?range=90').content.decode()
        self.assertIn("'=cmd()", csv)

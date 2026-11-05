from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.blog.models import Post
from apps.projects.models import Project
from .models import Announcement, Subscriber


@override_settings(SUBSCRIBERS_SYNC=True)
class SubscribeTests(TestCase):
    def post(self, **data):
        return self.client.post(reverse('subscribers:subscribe'), data)

    def test_subscribe_creates_and_dedupes(self):
        r = self.post(name='Ayesha Khan', email='Ayesha@Example.com')
        self.assertTrue(r.json()['ok'])
        s = Subscriber.objects.get()
        self.assertEqual((s.name, s.email, s.active), ('Ayesha Khan', 'ayesha@example.com', True))
        self.post(name='Ayesha K', email='ayesha@example.com')
        self.assertEqual(Subscriber.objects.count(), 1)

    def test_validation_and_honeypot(self):
        self.assertEqual(self.post(name='A', email='a@b.co').status_code, 400)
        self.assertEqual(self.post(name='Ali', email='nope').status_code, 400)
        self.assertTrue(self.post(name='Bot', email='bot@spam.com', website='http://x').json()['ok'])
        self.assertEqual(Subscriber.objects.count(), 0)

    def test_get_not_allowed(self):
        self.assertEqual(self.client.get(reverse('subscribers:subscribe')).status_code, 405)

    def test_unsubscribe(self):
        s = Subscriber.objects.create(name='Sam', email='sam@x.com')
        url = reverse('subscribers:unsubscribe', args=[s.token])
        self.assertContains(self.client.get(url), 'Yes, unsubscribe')
        self.client.post(url)
        s.refresh_from_db()
        self.assertFalse(s.active)

    def test_new_post_is_emailed_once(self):
        Subscriber.objects.create(name='Sam Lee', email='sam@x.com')
        Subscriber.objects.create(name='Off', email='off@x.com', active=False)
        p = Post.objects.create(title='Scaling Celery', excerpt='Lessons from queues.', body='Hello world', published_at=timezone.now())
        self.assertEqual([m.to for m in mail.outbox], [['sam@x.com']])
        m = mail.outbox[0]
        self.assertIn('Scaling Celery', m.subject)
        self.assertIn('Read the article', m.alternatives[0][0])
        self.assertIn('unsubscribe', m.alternatives[0][0].lower())
        p.title = 'Scaling Celery v2'
        p.save()
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(Announcement.objects.get().recipients, 1)

    def test_draft_then_publish_sends(self):
        Subscriber.objects.create(name='Sam', email='sam@x.com')
        p = Post.objects.create(title='Draft', excerpt='x', body='y', published=False)
        self.assertEqual(len(mail.outbox), 0)
        p.published = True
        p.save()
        self.assertEqual(len(mail.outbox), 1)

    def test_case_study_emailed_but_plain_project_not(self):
        Subscriber.objects.create(name='Sam', email='sam@x.com')
        Project.objects.create(title='Plain app', summary='s')
        self.assertEqual(len(mail.outbox), 0)
        Project.objects.create(title='BTR Mall — Marketplace', summary='s', case_study=True, card_badge='Featured')
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Featured', mail.outbox[0].alternatives[0][0])


@override_settings(SUBSCRIBERS_SYNC=True)
class DashboardTests(TestCase):
    def setUp(self):
        from django.contrib.auth import get_user_model
        self.u = get_user_model().objects.create_user('boss', 'boss@x.com', 'pw12345!x', is_staff=True)
        self.client.force_login(self.u)
        Subscriber.objects.create(name='Sam Lee', email='sam@x.com')

    def test_page_and_send(self):
        url = reverse('dashboard:subscribers')
        self.assertContains(self.client.get(url), 'sam@x.com')
        self.client.post(url, {'action': 'send', 'title': 'Open to contracts', 'text': 'Free from December.', 'link': '/services/', 'button': 'See services'})
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('http', mail.outbox[0].alternatives[0][0])
        self.assertEqual(Announcement.objects.get().kind, 'update')

    def test_requires_staff(self):
        self.client.logout()
        self.assertEqual(self.client.get(reverse('dashboard:subscribers')).status_code, 302)

from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

from apps.blog.models import Post
from apps.experience.models import Experience
from apps.projects.models import Project
from apps.siteconfig.models import SiteSettings


class ChatbotTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_answers_from_published_project_with_source_link(self):
        project = Project.objects.create(
            title='MarketHub',
            summary='A Django marketplace with vendor dashboards and payment workflows.',
            published=True,
        )

        response = self.client.post(
            reverse('chatbot:answer'),
            {'question': 'Tell me about the marketplace project'},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn('MarketHub', payload['answer'])
        self.assertIn('Django marketplace', payload['answer'])
        self.assertEqual(payload['sources'], [{'title': 'MarketHub', 'url': project.get_absolute_url()}])

    def test_does_not_retrieve_unpublished_projects_or_articles(self):
        Project.objects.create(title='Secret marketplace', summary='Private Django shop', published=False)
        Post.objects.create(
            title='Hidden article',
            slug='hidden-article',
            excerpt='Private Django guide',
            body='A private article about Django.',
            published=False,
        )

        response = self.client.post(reverse('chatbot:answer'), {'question': 'Tell me about Django'})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['sources'], [])
        self.assertNotIn('Secret marketplace', response.json()['answer'])

    def test_unknown_question_has_clear_english_fallback(self):
        response = self.client.post(
            reverse('chatbot:answer'),
            {'question': 'What is the capital of Japan?'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("couldn't find", response.json()['answer'])
        self.assertEqual(response.json()['sources'], [])

    def test_project_count_question_reports_total_and_live_count(self):
        Project.objects.create(title='Live One', summary='First live project.', status=Project.STATUS_LIVE)
        Project.objects.create(title='Live Two', summary='Second live project.', status=Project.STATUS_LIVE)
        Project.objects.create(title='In Progress', summary='A work in progress.', status=Project.STATUS_PROGRESS)

        response = self.client.post(
            reverse('chatbot:answer'),
            {'question': 'how many projects done Nouman'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn('3 published projects', response.json()['answer'])
        self.assertIn('2 are marked Live', response.json()['answer'])
        self.assertEqual(response.json()['sources'], [{'title': 'Projects', 'url': '/projects/'}])

    def test_office_question_uses_current_work_data_without_guessing_location(self):
        Experience.objects.create(
            role='Founder & CEO',
            organization='Xvera Labs',
            date_range='2026 — Present',
        )
        Experience.objects.create(
            role='Python Backend Engineer',
            organization='TheTechFury',
            date_range='May 2025 — Present',
        )
        SiteSettings.objects.create(open_onsite=True)

        response = self.client.post(
            reverse('chatbot:answer'),
            {'question': 'are Nouman doing work in any office now these days'},
        )

        self.assertEqual(response.status_code, 200)
        answer = response.json()['answer']
        self.assertIn('Founder & CEO at Xvera Labs', answer)
        self.assertIn('Python Backend Engineer at TheTechFury', answer)
        self.assertIn('does not say whether Nouman currently works from a physical office', answer)
        self.assertIn('open to on-site roles', answer)

    def test_rejects_empty_and_overlong_questions(self):
        empty = self.client.post(reverse('chatbot:answer'), {'question': '  '})
        long = self.client.post(reverse('chatbot:answer'), {'question': 'x' * 501})

        self.assertEqual(empty.status_code, 400)
        self.assertEqual(long.status_code, 400)

    def test_answer_endpoint_only_accepts_post(self):
        self.assertEqual(self.client.get(reverse('chatbot:answer')).status_code, 405)

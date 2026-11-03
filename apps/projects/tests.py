from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from .models import Project


class ParserTests(TestCase):
    def test_parsers(self):
        p = Project(title='X — Y', summary='s', challenge='a\r\n\r\nb\n\n\n', metrics='200+|tests\n\nFast| really |x',
                    architecture='Caddy|HTTPS\nDB', results='one\n two \n', lessons='', solution='z')
        self.assertEqual(p.challenge_paras, ['a', 'b'])
        self.assertEqual(p.solution_paras, ['z'])
        self.assertEqual(p.lessons_paras, [])
        self.assertEqual(p.result_list, ['one', 'two'])
        self.assertEqual(p.metric_list, [{'value': '200+', 'label': 'tests'}, {'value': 'Fast', 'label': 'really |x'}])
        self.assertEqual(p.architecture_steps, [{'label': 'Caddy', 'detail': 'HTTPS'}, {'label': 'DB', 'detail': ''}])


class SeedTests(TestCase):
    def setUp(self):
        call_command('seed_projects', verbosity=0)

    def test_four_case_studies(self):
        slugs = list(Project.objects.filter(case_study=True).order_by('order_in_showcase').values_list('slug', flat=True))
        self.assertEqual(slugs, ['btr-mall', 'dinex', 'goal-line-report', 'elecmech'])
        for p in Project.objects.filter(case_study=True):
            self.assertTrue(p.metric_list and p.architecture_steps and p.result_list and p.challenge_paras and p.solution_paras)

    def test_idempotent_and_keeps_edits(self):
        Project.objects.filter(slug='dinex').update(summary='edited')
        call_command('seed_projects', verbosity=0)
        self.assertEqual(Project.objects.filter(slug='dinex').count(), 1)
        self.assertEqual(Project.objects.get(slug='dinex').summary, 'edited')
        self.assertEqual(Project.objects.get(slug='dinex').tags.count(), 9)

    def test_views(self):
        r = self.client.get(reverse('projects:projects'))
        self.assertEqual(len(r.context['case_studies']), 4)
        r = self.client.get(reverse('projects:detail', args=['dinex']))
        self.assertEqual(r.status_code, 200)
        self.assertIn('related', r.context)
        self.assertLessEqual(len(r.context['related']), 2)
        self.assertEqual(r.context['project'].case_study_url, '/projects/dinex/')

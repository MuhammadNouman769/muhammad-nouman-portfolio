from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from .models import Project, ProjectTag


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
        self.assertEqual(r.status_code, 200)
        self.assertLessEqual(len(r.context['projects']), 12)
        self.assertContains(r, 'id="all"')
        self.assertNotContains(r, 'id="case-studies"')
        self.assertContains(r, 'Everything I have built')
        self.assertContains(r, 'Filter by status')
        r = self.client.get(reverse('projects:case_studies'))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.context['case_studies']), 4)
        self.assertContains(r, 'id="case-studies"')
        self.assertContains(r, 'Case studies')
        self.assertContains(r, 'Everything I have built')
        self.assertContains(r, 'Search projects')
        r = self.client.get(reverse('projects:detail', args=['dinex']))
        self.assertEqual(r.status_code, 200)
        self.assertIn('related', r.context)
        self.assertLessEqual(len(r.context['related']), 2)
        self.assertEqual(r.context['project'].case_study_url, '/projects/dinex/')

    def test_header_links_to_separate_case_studies_and_projects_pages(self):
        response = self.client.get(reverse('home:home'))
        self.assertContains(response, f'href="{reverse("projects:case_studies")}"')
        self.assertContains(response, f'href="{reverse("projects:projects")}"')
        self.assertContains(response, 'Case studies')
        self.assertContains(response, '>Projects</a>')

    def test_projects_are_paginated_in_batches_of_twelve(self):
        for number in range(13):
            Project.objects.create(
                title=f'Pagination project {number}',
                summary='A project added to test pagination.',
                published=True,
                order=100 + number,
            )

        first_page = self.client.get(reverse('projects:projects'))
        self.assertEqual(len(first_page.context['projects']), 12)
        self.assertTrue(first_page.context['page_obj'].has_next())
        self.assertContains(first_page, 'Project pages')

        second_page = self.client.get(reverse('projects:projects'), {'page': 2})
        self.assertEqual(second_page.context['page_obj'].number, 2)
        self.assertEqual(second_page.context['page_obj'].start_index(), 13)
        self.assertLessEqual(len(second_page.context['projects']), 12)

    def test_project_filters_apply_before_pagination_and_are_preserved(self):
        for number in range(13):
            project = Project.objects.create(
                title=f'Searchable project {number}',
                summary='Needle result for pagination.',
                status=Project.STATUS_LIVE,
                published=True,
                order=100 + number,
            )
            ProjectTag.objects.create(project=project, name='Python')

        params = {'q': 'Needle', 'status': Project.STATUS_LIVE, 'tech': 'Python'}
        first_page = self.client.get(reverse('projects:projects'), params)
        self.assertEqual(first_page.context['page_obj'].paginator.count, 13)
        self.assertEqual(len(first_page.context['projects']), 12)
        live_filter = next(option for option in first_page.context['status_filters'] if option['label'] == 'Live')
        self.assertIn('q=Needle', live_filter['url'])
        self.assertIn('tech=Python', live_filter['url'])
        self.assertNotIn('page=', live_filter['url'])
        next_page_link = next(page for page in first_page.context['pagination_pages'] if page['number'] == 2)
        self.assertIn('q=Needle', next_page_link['url'])
        self.assertIn('status=live', next_page_link['url'])
        self.assertIn('tech=Python', next_page_link['url'])
        next_page = self.client.get(reverse('projects:projects'), {**params, 'page': 2})
        self.assertEqual(len(next_page.context['projects']), 1)
        self.assertEqual(next_page.context['status_filter'], Project.STATUS_LIVE)

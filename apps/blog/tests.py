import xml.etree.ElementTree as ET

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse

from . import markdown
from .models import Category, Post


class MarkdownTests(TestCase):
    def test_basic_blocks(self):
        html = markdown.render('## Title\n\nHello **bold** and *it* and `x < y`.\n\n- a\n- b\n\n1. one\n2. two\n\n> quote')
        for frag in ('<h2 id="title">Title</h2>', '<strong>bold</strong>', '<em>it</em>', '<code>x &lt; y</code>',
                     '<ul><li>a</li><li>b</li></ul>', '<ol><li>one</li><li>two</li></ol>', '<blockquote>'):
            self.assertIn(frag, html)

    def test_code_fence_is_escaped(self):
        html = markdown.render('```python\nprint("<b>")\n```')
        self.assertIn('<pre><code class="lang-python">print(&quot;&lt;b&gt;&quot;)</code></pre>', html)

    def test_script_is_escaped(self):
        html = markdown.render('Hi <script>alert(1)</script>\n\n## <img src=x onerror=alert(1)>')
        self.assertNotIn('<script', html)
        self.assertNotIn('<img', html)

    def test_dangerous_links_stripped(self):
        for bad in ('javascript:alert(1)', 'JaVaScRiPt:alert(1)', 'java\tscript:alert(1)', 'data:text/html,x', '//evil.com'):
            html = markdown.render(f'[click]({bad})')
            self.assertNotIn('href', html, bad)
        self.assertIn('href="https://ok.com"', markdown.render('[a](https://ok.com)'))
        self.assertIn('rel="noopener noreferrer"', markdown.render('[a](https://ok.com)'))
        self.assertIn('<a href="/blog/">', markdown.render('[a](/blog/)'))

    def test_quote_in_href_cannot_break_attribute(self):
        html = markdown.render('[a](https://x.com/"onmouseover="alert(1))')
        self.assertNotIn('onmouseover="', html)

    def test_toc_and_unique_ids(self):
        t = markdown.toc('## A\n\n### B\n\n## A')
        self.assertEqual(t, [('a', 'A', 2), ('b', 'B', 3), ('a-2', 'A', 2)])


class BlogViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('seed_blog', verbosity=0)

    def test_seed_is_idempotent(self):
        n = Post.objects.count()
        call_command('seed_blog', verbosity=0)
        self.assertEqual(Post.objects.count(), n)
        self.assertEqual(n, 6)
        self.assertEqual(Post.objects.filter(featured=True).count(), 2)
        self.assertEqual(Category.objects.count(), 4)

    def test_index_and_filter(self):
        r = self.client.get(reverse('blog:index'))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.context['posts']), 6)
        self.assertTrue(r.context['featured'].featured)
        r = self.client.get(reverse('blog:index'), {'c': 'devops'})
        self.assertEqual(r.context['active_category'].slug, 'devops')
        self.assertEqual(len(r.context['posts']), 1)

    def test_detail_context(self):
        p = Post.objects.get(slug='designing-a-multi-vendor-order-model')
        r = self.client.get(p.get_absolute_url())
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.context['related'])
        self.assertNotIn(p, r.context['related'])
        self.assertTrue(r.context['prev_post'] or r.context['next_post'])
        self.assertGreaterEqual(p.read_minutes, 2)

    def test_unpublished_404_but_staff_preview(self):
        p = Post.objects.first()
        p.published = False
        p.save()
        self.assertEqual(self.client.get(p.get_absolute_url()).status_code, 404)
        self.assertNotIn(p, self.client.get(reverse('blog:index')).context['posts'])
        User = get_user_model()
        User.objects.create_user('s', password='pw-12345-xyz', is_staff=True)
        self.client.login(username='s', password='pw-12345-xyz')
        r = self.client.get(p.get_absolute_url())
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.context['is_preview'])

    def test_missing_slug_404(self):
        self.assertEqual(self.client.get('/blog/nope/').status_code, 404)

    def test_sitemap_lists_posts(self):
        body = self.client.get('/sitemap.xml').content.decode()
        ET.fromstring(body)
        self.assertIn('/blog/', body)
        for p in Post.objects.all():
            self.assertIn(p.get_absolute_url(), body)

    def test_feed_is_valid_rss(self):
        r = self.client.get(reverse('blog:feed'))
        self.assertEqual(r.status_code, 200)
        root = ET.fromstring(r.content)
        self.assertEqual(root.tag, 'rss')
        self.assertEqual(len(root.findall('./channel/item')), 6)

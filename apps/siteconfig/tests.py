import io

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from PIL import Image

from .models import Banner


def png(name='b.png'):
    buf = io.BytesIO()
    Image.new('RGB', (160, 100), '#3452e8').save(buf, 'PNG')
    return SimpleUploadedFile(name, buf.getvalue(), content_type='image/png')


@override_settings(MEDIA_ROOT='/tmp/test_media_banners')
class BannerTests(TestCase):
    def test_home_slide_and_page_banner_render(self):
        Banner.objects.create(placement='home', title='Hello slide', image=png(), button_text='Go', button_url='/projects/')
        Banner.objects.create(placement='about', title='About pic', image=png('a.png'))
        Banner.objects.create(placement='blog', title='Hidden pic', image=png('c.png'), active=False)
        home = self.client.get('/')
        self.assertContains(home, 'Hello slide')
        self.assertContains(self.client.get('/about/'), 'bn-photo')
        self.assertNotContains(self.client.get('/blog/'), 'bn-photo')

    def test_dashboard_can_add_banner(self):
        user = get_user_model().objects.create_superuser('boss', 'b@x.com', 'pw-12345-x')
        self.client.force_login(user)
        r = self.client.post('/dashboard/content/banners/new/', {'placement': 'home', 'title': 'New', 'image': png(), 'accent': '#112233', 'active': 'on'})
        self.assertEqual(r.status_code, 302, getattr(r, 'content', b'')[:300])
        self.assertEqual(Banner.objects.count(), 1)

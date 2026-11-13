"""Fill blog, projects, experience, messages and subscribers with dummy data (12-15+ per section).

    python manage.py seed_dummy            # add (safe to run twice)
    python manage.py seed_dummy --remove   # delete only what this command created
"""
import json
from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.models.signals import post_save
from django.utils import timezone

from apps.blog.models import Category, Post
from apps.contact.models import ContactMessage
from apps.experience.models import Experience, ExperienceHighlight
from apps.home import demo_data as D
from apps.projects.models import Project, ProjectFeature, ProjectTag
from apps.subscribers import signals as sub_signals
from apps.subscribers.models import Subscriber

MARK = settings.BASE_DIR / '.demo_seed.json'


class Command(BaseCommand):
    help = 'Add or remove dummy content for design and QA.'

    def add_arguments(self, parser):
        parser.add_argument('--remove', action='store_true')

    def handle(self, *a, **o):
        data = json.loads(MARK.read_text()) if MARK.exists() else {}
        if o['remove']:
            for model, key in ((Post, 'posts'), (Project, 'projects'), (Experience, 'experience'), (ContactMessage, 'messages'), (Subscriber, 'subscribers'), (Category, 'categories')):
                n = model.objects.filter(pk__in=data.get(key, [])).delete()[0]
                self.stdout.write(f'removed {key}: {n}')
            MARK.unlink(missing_ok=True)
            return
        # Never email real subscribers about dummy content.
        post_save.disconnect(sub_signals._post_saved, sender=Post)
        post_save.disconnect(sub_signals._project_saved, sender=Project)
        try:
            self._add(data)
        finally:
            post_save.connect(sub_signals._post_saved, sender=Post)
            post_save.connect(sub_signals._project_saved, sender=Project)
        MARK.write_text(json.dumps(data))
        for label, model in (('Posts', Post), ('Categories', Category), ('Projects', Project), ('Experience', Experience), ('Messages', ContactMessage), ('Subscribers', Subscriber)):
            self.stdout.write(f'{label}: {model.objects.count()}')

    def _track(self, data, key, obj):
        data.setdefault(key, [])
        if obj.pk not in data[key]:
            data[key].append(obj.pk)

    def _add(self, data):
        cats = {}
        for i, name in enumerate(D.CATEGORIES):
            c, made = Category.objects.get_or_create(name=name, defaults={'order': 10 + i})
            cats[name] = c
            if made:
                self._track(data, 'categories', c)
        for name in ('Django', 'Architecture', 'DevOps', 'Career'):
            cats[name] = Category.objects.filter(name=name).first() or Category.objects.create(name=name)
        now = timezone.now()
        for p in D.POSTS:
            if Post.objects.filter(title=p['title']).exists():
                continue
            post = Post.objects.create(title=p['title'], excerpt=p['excerpt'], body=p['body'], category=cats[p['cat']], tags=p['tags'],
                                       cover_accent=p['accent'], published_at=now - timedelta(days=p['days']), meta_description=p['excerpt'][:170])
            self._track(data, 'posts', post)
        for p in D.PROJECTS:
            if Project.objects.filter(title=p['title']).exists():
                continue
            pr = Project.objects.create(title=p['title'], summary=p['summary'], body=p['body'], status=p['status'], year=p['year'],
                                        kind=p['kind'], featured=False, role='Backend engineer', accent='#9a3412')
            for t in p['tags']:
                ProjectTag.objects.create(project=pr, name=t)
            for i, f in enumerate(p['features']):
                ProjectFeature.objects.create(project=pr, text=f, order=i)
            self._track(data, 'projects', pr)
        base = Experience.objects.count()
        for i, e in enumerate(D.EXPERIENCE):
            if Experience.objects.filter(role=e['role'], organization=e['org']).exists():
                continue
            ex = Experience.objects.create(role=e['role'], organization=e['org'], date_range=e['dates'], order=base + i)
            for j, t in enumerate(e['points']):
                ExperienceHighlight.objects.create(experience=ex, text=t, order=j)
            self._track(data, 'experience', ex)
        for i, (n, em, sub, msg) in enumerate(D.MESSAGES):
            if ContactMessage.objects.filter(email=em).exists():
                continue
            m = ContactMessage.objects.create(name=n, email=em, subject=sub, message=msg, is_read=i > 3, is_starred=i in (0, 3), replied=i in (5, 6))
            ContactMessage.objects.filter(pk=m.pk).update(created_at=now - timedelta(days=i * 2, hours=i))
            self._track(data, 'messages', m)
        for i, n in enumerate(D.SUBSCRIBERS):
            em = n.lower().replace(' ', '.') + '@example.com'
            if Subscriber.objects.filter(email=em).exists():
                continue
            s = Subscriber.objects.create(name=n, email=em, source='demo', active=i % 7 != 6)
            Subscriber.objects.filter(pk=s.pk).update(created_at=now - timedelta(days=i * 3))
            self._track(data, 'subscribers', s)

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone

from apps.blog.models import Post
from apps.projects.models import Project
from .emails import absolute, announce
from .models import Announcement


def _was_live(model, pk, field='published'):
    if not pk:
        return False
    return bool(model.objects.filter(pk=pk).values_list(field, flat=True).first())


@receiver(pre_save, sender=Post)
def _post_before(sender, instance, **kw):
    instance._was_live = _was_live(Post, instance.pk)


@receiver(pre_save, sender=Project)
def _project_before(sender, instance, **kw):
    instance._was_live = _was_live(Project, instance.pk) and Project.objects.filter(pk=instance.pk, case_study=True).exists()


@receiver(post_save, sender=Post)
def _post_saved(sender, instance, raw=False, **kw):
    if raw or not instance.published or instance.published_at > timezone.now() or getattr(instance, '_was_live', False):
        return
    if Announcement.objects.filter(kind='post', object_id=instance.pk).exists():
        return
    announce('post', instance.title, object_id=instance.pk, subject=f'New article: {instance.title}',
             kicker='New article' + (f' · {instance.category.name}' if instance.category_id else ''), title=instance.title,
             text=instance.excerpt, url=absolute(instance.get_absolute_url()), button='Read the article',
             accent=instance.cover_accent or '#3452e8')


@receiver(post_save, sender=Project)
def _project_saved(sender, instance, raw=False, **kw):
    if raw or not (instance.published and instance.case_study) or getattr(instance, '_was_live', False):
        return
    if Announcement.objects.filter(kind='project', object_id=instance.pk).exists():
        return
    announce('project', instance.card_heading, object_id=instance.pk, subject=f'New case study: {instance.card_heading}',
             kicker='New case study', title=instance.card_heading, text=instance.card_text,
             url=absolute(instance.get_absolute_url()), button='Read the case study', badge=instance.card_badge,
             accent=instance.accent or '#3452e8')

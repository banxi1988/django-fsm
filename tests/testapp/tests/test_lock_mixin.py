from django.db import models
from django_fsm_ex import ConcurrentTransitionMixin, transition, FSMField, ConcurrentTransition

import pytest
pytestmark = pytest.mark.django_db

class LockedBlogPost(ConcurrentTransitionMixin, models.Model):
    state = FSMField(default='new', protected=True)
    text = models.CharField(max_length=50)

    @transition(field=state, source='new', target='published')
    def publish(self):
        pass

    @transition(field=state, source='published', target='removed')
    def remove(self):
        pass

    class Meta:
        app_label = 'testapp'


class ExtendedBlogPost(LockedBlogPost):
    review_state = FSMField(default='waiting', protected=True)
    notes = models.CharField(max_length=50)

    @transition(field=review_state, source='waiting', target='rejected')
    def reject(self):
        pass

    class Meta:
        app_label = 'testapp'


def test_create_succeed():
    LockedBlogPost.objects.create(text='test_create_succeed')

def test_crud_succeed():
    post = LockedBlogPost(text='test_crud_succeed')
    post.publish()
    post.save()

    post = LockedBlogPost.objects.get(pk=post.pk)
    assert ('published' == post.state)
    post.text = 'test_crud_succeed2'
    post.save()

    post = LockedBlogPost.objects.get(pk=post.pk)
    assert ('test_crud_succeed2' == post.text)

def test_save_and_change_succeed():
    post = LockedBlogPost(text='test_crud_succeed')
    post.publish()
    post.save()

    post.remove()
    post.save()

def test_concurent_modifications_raise_exception():
    post1 = LockedBlogPost.objects.create()
    post2 = LockedBlogPost.objects.get(pk=post1.pk)

    post1.publish()
    post1.save()

    post2.text = 'aaa'
    post2.publish()
    with pytest.raises(ConcurrentTransition):
        post2.save()

def test_inheritance_crud_succeed():
    post = ExtendedBlogPost(text='test_inheritance_crud_succeed', notes='reject me')
    post.publish()
    post.save()

    post = ExtendedBlogPost.objects.get(pk=post.pk)
    assert ('published' == post.state)
    post.text = 'test_inheritance_crud_succeed2'
    post.reject()
    post.save()

    post = ExtendedBlogPost.objects.get(pk=post.pk)
    assert ('rejected' == post.review_state)
    assert ('test_inheritance_crud_succeed2' == post.text)

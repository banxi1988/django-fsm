from django.db import models
from django.test import TestCase
from django_fsm.errors import TransitionNotAllowed
from django_fsm.transition import can_proceed
from django_fsm.decorators import transition
from django_fsm.fields import FSMKeyField

FK_AVAILABLE_STATES = (
    ('New', '_NEW_'),
    ('Published', '_PUBLISHED_'),
    ('Hidden', '_HIDDEN_'),
    ('Removed', '_REMOVED_'),
    ('Stolen', '_STOLEN_'),
    ('Moderated', '_MODERATED_'))

import pytest
pytestmark = pytest.mark.django_db

class DBState(models.Model):
    id = models.CharField(primary_key=True, max_length=50)

    label = models.CharField(max_length=255)

    def __unicode__(self):
        return self.label

    class Meta:
        app_label = 'django_fsm'


class FKBlogPost(models.Model):
    state = FSMKeyField(DBState, default='new', protected=True, on_delete=models.CASCADE)

    @transition(field=state, source='new', target='published')
    def publish(self):
        pass

    @transition(field=state, source='published')
    def notify_all(self):
        pass

    @transition(field=state, source='published', target='hidden')
    def hide(self):
        pass

    @transition(field=state, source='new', target='removed')
    def remove(self):
        raise Exception('Upss')

    @transition(field=state, source=['published', 'hidden'], target='stolen')
    def steal(self):
        pass

    @transition(field=state, source='*', target='moderated')
    def moderate(self):
        pass

    class Meta:
        app_label = 'django_fsm'

@pytest.fixture()
def model():
    for item in FK_AVAILABLE_STATES:
        DBState.objects.create(pk=item[0], label=item[1])
    return FKBlogPost()

def test_initial_state_instatiated(model):
    assert (model.state == 'new')

def test_known_transition_should_succeed(model):
    assert (can_proceed(model.publish))
    model.publish()
    assert (model.state == 'published')

    assert (can_proceed(model.hide))
    model.hide()
    assert (model.state == 'hidden')

def test_unknow_transition_fails(model):
    assert not (can_proceed(model.hide))
    pytest.raises(TransitionNotAllowed, model.hide)

def test_state_non_changed_after_fail(model):
    assert (can_proceed(model.remove))
    pytest.raises(Exception, model.remove)
    assert (model.state == 'new')

def test_allowed_null_transition_should_succeed(model):
    assert (can_proceed(model.publish))
    model.publish()
    model.notify_all()
    assert (model.state == 'published')

def test_unknow_null_transition_should_fail(model):
    pytest.raises(TransitionNotAllowed, model.notify_all)
    assert (model.state == 'new')

def test_mutiple_source_support_path_1_works(model):
    model.publish()
    model.steal()
    assert (model.state == 'stolen')

def test_mutiple_source_support_path_2_works(model):
    model.publish()
    model.hide()
    model.steal()
    assert (model.state == 'stolen')

def test_star_shortcut_succeed(model):
    assert (can_proceed(model.moderate))
    model.moderate()
    assert (model.state == 'moderated')


class BlogPostStatus(models.Model):
  name = models.CharField(max_length=10, unique=True)
  objects = models.Manager()

  class Meta:
      app_label = 'django_fsm'


class BlogPostWithFKState(models.Model):
  status = FSMKeyField(BlogPostStatus, default=lambda: BlogPostStatus.objects.get(name="new"),on_delete=models.CASCADE)

  @transition(field=status, source='new', target='published')
  def publish(self):
      pass

  @transition(field=status, source='published', target='hidden')
  def hide(self):
      pass


@pytest.fixture()
def model2():
    BlogPostStatus.objects.create(name="new")
    BlogPostStatus.objects.create(name="published")
    BlogPostStatus.objects.create(name="hidden")
    return BlogPostWithFKState()

def test_model2_known_transition_should_succeed(model):
    model.publish()
    assert (model.state == 'published')

    model.hide()
    assert (model.state == 'hidden')

def test_model2_unknow_transition_fails(model):
    pytest.raises(TransitionNotAllowed, model.hide)

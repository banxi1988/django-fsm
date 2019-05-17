import pytest
from django.db import models
from django.test import TestCase
from django_fsm.errors import TransitionNotAllowed
from django_fsm.transition import can_proceed
from django_fsm.decorators import transition
from django_fsm.fields import FSMField


def condition_func(instance):
  assert isinstance(instance, models.Model)
  return True


class BlogPostWithConditions(models.Model):
    state = FSMField(default='new')

    def model_condition(self):
        return True

    def unmet_condition(self):
        return False

    @transition(field=state, source='new', target='published',
                conditions=[condition_func, model_condition])
    def publish(self):
        pass

    @transition(field=state, source='published', target='destroyed',
                conditions=[condition_func, unmet_condition])
    def destroy(self):
        pass

@pytest.fixture
def model():
    return BlogPostWithConditions()


def test_initial_staet(model):
    assert (model.state == 'new')

def test_known_transition_should_succeed(model):
    assert (can_proceed(model.publish))
    model.publish()
    assert (model.state == 'published')

def test_unmet_condition(model):
    model.publish()
    assert (model.state == 'published')
    assert not (can_proceed(model.destroy))
    pytest.raises(TransitionNotAllowed, model.destroy)

    assert (can_proceed(model.destroy, check_conditions=False))

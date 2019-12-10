import pytest
from django.db import models
from django_fsm_ex.errors import TransitionNotAllowed
from django_fsm_ex.transition import can_proceed
from django_fsm_ex.decorators import transition
from django_fsm_ex.fields import FSMField, get_fsm_meta


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

    @transition(field=state, source='new', target='online' )
    def online(self):
      pass

@pytest.fixture
def model():
    return BlogPostWithConditions()

def test_conditions_met_fail_if_no_transition(model):
  fsm_meta = get_fsm_meta(model.publish)
  assert fsm_meta
  assert not fsm_meta.conditions_met(model, "notastate")

def test_conditions_met_if_no_condition(model):
  fsm_meta = get_fsm_meta(model.online)
  assert fsm_meta.conditions_met(model, "new")


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



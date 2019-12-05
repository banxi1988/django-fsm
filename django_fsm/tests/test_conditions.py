import pytest
from django.db import models
from django_fsm.errors import TransitionNotAllowed
from django_fsm.transition import can_proceed, get_fsm_meta
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

    @transition(field=state, source='new', target='online' )
    def online(self):
      pass

@pytest.fixture
def model():
    return BlogPostWithConditions()

def test_conditions_met_fail_if_no_transition(model):
  fsm_meta = get_fsm_meta(method=model.publish,field=BlogPostWithConditions.state)
  assert fsm_meta
  assert not fsm_meta.conditions_met(model, "notastate")

def test_conditions_met_if_no_condition(model):
  fsm_meta = get_fsm_meta(method=model.online, field=BlogPostWithConditions.state)
  assert fsm_meta.conditions_met(model, "new")


def test_initial_staet(model):
    assert (model.state == 'new')

def test_known_transition_should_succeed(model):
    assert (BlogPostWithConditions.state.can_proceed(model.publish))
    model.publish()
    assert (model.state == 'published')

def test_unmet_condition(model):
    model.publish()
    assert (model.state == 'published')
    assert not (BlogPostWithConditions.state.can_proceed(model.destroy))
    pytest.raises(TransitionNotAllowed, model.destroy)

    assert (BlogPostWithConditions.state.can_proceed(model.destroy, check_conditions=False))



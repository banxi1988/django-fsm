import importlib

import pytest
from django.db import models
from django.test import TestCase

from django_fsm.errors import TransitionNotAllowed
from django_fsm.transition import can_proceed
from django_fsm.decorators import transition
from django_fsm.fields import FSMField
from django_fsm.signals import pre_transition, post_transition


class BlogPost(models.Model):
    state = FSMField(default='new')

    @transition(field=state, source='new', target='published')
    def publish(self):
        pass

    @transition(source='published', field=state)
    def notify_all(self):
        pass

    @transition(source='published', target='hidden', field=state)
    def hide(self):
        pass

    @transition(source='new', target='removed', field=state)
    def remove(self):
        raise Exception('Upss')

    @transition(source=['published', 'hidden'], target='stolen', field=state)
    def steal(self):
        pass

    @transition(source='*', target='moderated', field=state)
    def moderate(self):
        pass

    @transition(source='+', target='blocked', field=state)
    def block(self):
        pass

    @transition(source='*', target='', field=state)
    def empty(self):
        pass

@pytest.fixture
def model():
    return BlogPost()

def test_initial_state_instantiated(model):
    assert model.state == 'new'

def test_known_transition_should_succeed(model):
    assert BlogPost.state.can_proceed(model.publish)
    model.publish()
    assert model.state == 'published'

    assert BlogPost.state.can_proceed(model.hide)
    model.hide()
    assert model.state == 'hidden'

def test_unknown_transition_fails(model):
    assert not (BlogPost.state.can_proceed(model.hide))
    pytest.raises(TransitionNotAllowed, model.hide)

def test_state_non_changed_after_fail(model):
    assert (BlogPost.state.can_proceed(model.remove))
    pytest.raises(Exception, model.remove)
    assert (model.state == 'new')

def test_allowed_null_transition_should_succeed(model):
    model.publish()
    model.notify_all()
    assert (model.state == 'published')

def test_unknown_null_transition_should_fail(model):
    pytest.raises(TransitionNotAllowed, model.notify_all)
    assert (model.state == 'new')

def test_multiple_source_support_path_1_works(model):
    model.publish()
    model.steal()
    assert (model.state == 'stolen')

def test_multiple_source_support_path_2_works(model):
    model.publish()
    model.hide()
    model.steal()
    assert (model.state == 'stolen')


def test_star_shortcut_succeed(model):
    assert (BlogPost.state.can_proceed(model.moderate))
    model.moderate()
    assert (model.state == 'moderated')

def test_plus_shortcut_succeeds_for_other_source(model):
    """Tests that the '+' shortcut succeeds for a source
    other than the target.
    """
    assert (BlogPost.state.can_proceed(model.block))
    model.block()
    assert (model.state == 'blocked')

def test_plus_shortcut_fails_for_same_source(model):
    """Tests that the '+' shortcut fails if the source
    equals the target.
    """
    model.block()
    assert not (BlogPost.state.can_proceed(model.block))
    pytest.raises(TransitionNotAllowed, model.block)

def test_empty_string_target(model):
    model.empty()
    assert (model.state == '')


class StateSignalsTests(TestCase):
    def setUp(self):
        self.model = BlogPost()
        self.pre_transition_called = False
        self.post_transition_called = False
        pre_transition.connect(self.on_pre_transition, sender=BlogPost)
        post_transition.connect(self.on_post_transition, sender=BlogPost)

    def on_pre_transition(self, sender, instance, name, source, target, **kwargs):
        assert (instance.state == source)
        self.pre_transition_called = True

    def on_post_transition(self, sender, instance, name, source, target, **kwargs):
        assert (instance.state == target)
        self.post_transition_called = True

    def test_signals_called_on_valid_transition(self):
        self.model.publish()
        assert (self.pre_transition_called)
        assert (self.post_transition_called)

    def test_signals_not_called_on_invalid_transition(self):
        pytest.raises(TransitionNotAllowed, self.model.hide)
        assert not (self.pre_transition_called)
        assert not (self.post_transition_called)




def test_available_conditions_from_new(model):
    transitions = model.get_available_state_transitions()
    actual = set((transition.source, transition.target) for transition in transitions)
    expected = {('*', 'moderated'), ('new', 'published'), ('new', 'removed'), ('*', ''), ('+', 'blocked')}
    assert (actual == expected)

def test_available_conditions_from_published(model):
    model.publish()
    transitions = model.get_available_state_transitions()
    actual = set((transition.source, transition.target) for transition in transitions)
    expected = {('*', 'moderated'), ('published', None), ('published', 'hidden'), ('published', 'stolen'),
                ('*', ''), ('+', 'blocked')}
    assert (actual == expected)

def test_available_conditions_from_hidden(model):
    model.publish()
    model.hide()
    transitions = model.get_available_state_transitions()
    actual = set((transition.source, transition.target) for transition in transitions)
    expected = {('*', 'moderated'), ('hidden', 'stolen'), ('*', ''), ('+', 'blocked')}
    assert (actual == expected)

def test_available_conditions_from_stolen(model):
    model.publish()
    model.steal()
    transitions = model.get_available_state_transitions()
    actual = set((transition.source, transition.target) for transition in transitions)
    expected = {('*', 'moderated'), ('*', ''), ('+', 'blocked')}
    assert (actual == expected)

def test_available_conditions_from_blocked(model):
    model.block()
    transitions = model.get_available_state_transitions()
    actual = set((transition.source, transition.target) for transition in transitions)
    expected = {('*', 'moderated'), ('*', '')}
    assert (actual == expected)

def test_available_conditions_from_empty(model):
    model.empty()
    transitions = model.get_available_state_transitions()
    actual = set((transition.source, transition.target) for transition in transitions)
    expected = {('*', 'moderated'), ('*', ''), ('+', 'blocked')}
    assert (actual == expected)

def test_all_conditions(model):
    transitions = model.get_all_state_transitions()

    actual = set((transition.source, transition.target) for transition in transitions)
    expected = {('*', 'moderated'), ('new', 'published'), ('new', 'removed'), ('published', None),
                ('published', 'hidden'), ('published', 'stolen'), ('hidden', 'stolen'), ('*', ''), ('+', 'blocked')}
    assert (actual == expected)

def test_duplicate_source_error():
    with pytest.raises(AssertionError):
        class BlogPostDuplicateSource(models.Model):
            state = FSMField(default='new')

            @transition(field=state, source='new', target='online')
            @transition(field=state, source='new', target='published')
            def publish(self):
                pass
        assert BlogPostDuplicateSource

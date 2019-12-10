from django.db import models
from django.test import TestCase

from django_fsm.errors import TransitionNotAllowed
from django_fsm.transition import RETURN_VALUE, GET_STATE
from django_fsm.decorators import transition
from django_fsm.fields import FSMField
from django_fsm.signals import pre_transition, post_transition, transition_not_allowed, no_transition

import pytest
pytestmark = pytest.mark.django_db

class MultiResultTest(models.Model):
    state = FSMField(default='new')

    @transition(
        field=state,
        source='new',
        target=RETURN_VALUE('for_moderators', 'published'))
    def publish(self, is_public=False):
        return 'published' if is_public else 'for_moderators'

    @transition(
        field=state,
        source='for_moderators',
        target=GET_STATE(
            lambda self, allowed: 'published' if allowed else 'rejected',
            states=['published', 'rejected']
        )
    )
    def moderate(self, allowed):
        pass

    class Meta:
        app_label = 'testapp'


def test_return_state_succeed():
    instance = MultiResultTest()
    instance.publish(is_public=True)
    assert (instance.state == 'published')

def test_get_state_succeed():
    instance = MultiResultTest(state='for_moderators')
    instance.moderate(allowed=False)
    assert (instance.state == 'rejected')


class TestSignals(TestCase):
    def setUp(self):
        self.pre_transition_called = False
        self.post_transition_called = False
        self.transition_not_allowed_called = False
        pre_transition.connect(self.on_pre_transition, sender=MultiResultTest)
        post_transition.connect(self.on_post_transition, sender=MultiResultTest)
        transition_not_allowed.connect(self.on_transition_not_allowed,sender=MultiResultTest)
        no_transition.connect(self.on_no_transition,sender=MultiResultTest)

    def on_pre_transition(self, sender, instance, name, source, target, **kwargs):
        assert (instance.state == source)
        self.pre_transition_called = True

    def on_post_transition(self, sender, instance, name, source, target, **kwargs):
        self.assertEqual(instance.state, target)
        self.post_transition_called = True

    def on_transition_not_allowed(self,sender,instance,name, field, source,**kwargs):
        self.transition_not_allowed_called = True

    def on_no_transition(self,sender,instance,name, field, source,**kwargs):
        self.no_transition_called = True

    def test_signals_called_with_not_allowed_action(self):
        instance = MultiResultTest()
        with pytest.raises(TransitionNotAllowed):
            instance.moderate(is_allowed=True)
        assert self.no_transition_called

    def test_signals_called_with_get_state(self):
        instance = MultiResultTest(state='for_moderators')
        instance.moderate(allowed=False)
        assert (self.pre_transition_called)
        assert (self.post_transition_called)

    def test_signals_called_with_return_value(self):
        instance = MultiResultTest()
        instance.publish(is_public=True)
        assert (self.pre_transition_called)
        assert (self.post_transition_called)

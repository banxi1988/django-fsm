from django.db import models
from django.test import TestCase
from django_fsm.transition import can_proceed
from django_fsm.decorators import transition
from django_fsm.fields import FSMField


class DemoExceptTargetTransitionShortcut(models.Model):
    state = FSMField(default='new')

    @transition(field=state, source='new', target='published')
    def publish(self):
        pass

    @transition(field=state, source='+', target='removed')
    def remove(self):
        pass

    class Meta:
        app_label = 'testapp'


class Test(TestCase):
    def setUp(self):
        self.model = DemoExceptTargetTransitionShortcut()

    def test_usecase(self):
        assert (self.model.state == 'new')
        assert (can_proceed(self.model.remove))
        self.model.remove()

        assert (self.model.state == 'removed')
        assert not (can_proceed(self.model.remove))

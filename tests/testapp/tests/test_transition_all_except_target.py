from django.db import models
from django_fsm_ex import can_proceed, transition, FSMField

import pytest
pytestmark = pytest.mark.django_db

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

@pytest.fixture()
def model():
    return DemoExceptTargetTransitionShortcut()

def test_usecase(model):
    assert (model.state == 'new')
    assert (can_proceed(model.remove))
    model.remove()

    assert (model.state == 'removed')
    assert not (can_proceed(model.remove))

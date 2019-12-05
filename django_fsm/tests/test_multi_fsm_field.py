from django.db import models

from django_fsm.decorators import transition
from django_fsm.fields import FSMField

import pytest
pytestmark = pytest.mark.django_db

class MultiFsmStateFieldModel(models.Model):
    status1 = FSMField(default='new', protected=True)
    status2 = FSMField(default='new', protected=True)

    @transition(field=status1, source='new', target='published')
    @transition(field=status2, source='new', target='published')
    def publish(self):
        pass

    class Meta:
        app_label = 'django_fsm'


def test_can_support_multi_state_field_trans():
    instance = MultiFsmStateFieldModel()
    instance.publish()
    assert instance.status1 == 'published'
    assert instance.status2 == 'published'

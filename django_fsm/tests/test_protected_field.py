from django.db import models

from django_fsm.decorators import transition
from django_fsm.fields import FSMField

import pytest
pytestmark = pytest.mark.django_db

class ProtectedAccessModel(models.Model):
    status = FSMField(default='new', protected=True)

    @transition(field=status, source='new', target='published')
    def publish(self):
        pass

    class Meta:
        app_label = 'django_fsm'


def test_no_direct_access():
    instance = ProtectedAccessModel()
    assert (instance.status == 'new')

    def try_change():
        instance.status = 'change'

    pytest.raises(AttributeError, try_change)

    instance.publish()
    instance.save()
    assert (instance.status == 'published')

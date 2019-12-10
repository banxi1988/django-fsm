from django.db import models

from django_fsm_ex.transition import can_proceed
from django_fsm_ex.decorators import transition
from django_fsm_ex.fields import FSMField

import pytest
pytestmark = pytest.mark.django_db

class BaseModel(models.Model):
    state = FSMField(default='new')

    @transition(field=state, source='new', target='published')
    def publish(self):
        pass


class InheritedModel(BaseModel):
    @transition(field='state', source='published', target='sticked')
    def stick(self):
        pass

    class Meta:
        proxy = True

@pytest.fixture()
def model():
    return InheritedModel()

def test_known_transition_should_succeed(model):
    assert (can_proceed(model.publish))
    model.publish()
    assert (model.state == 'published')

    assert (can_proceed(model.stick))
    model.stick()
    assert (model.state == 'sticked')

def test_field_available_transitions_works(model):
    model.publish()
    assert (model.state == 'published')
    transitions = model.get_available_state_transitions()
    assert (['sticked'] == [data.target for data in transitions])

def test_field_all_transitions_base_model(model):
    transitions = BaseModel().get_all_state_transitions()
    assert ({('new' , 'published')} ==
                     set((data.source, data.target) for data in transitions))

def test_field_all_transitions_works(model):
    transitions = model.get_all_state_transitions()
    assert ({('new', 'published'), ('published', 'sticked')} ==
                     set((data.source, data.target) for data in transitions))

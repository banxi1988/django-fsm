from django.db import models
from django_fsm_ex.decorators import transition
from django_fsm_ex.fields import FSMField

import pytest
pytestmark = pytest.mark.django_db

class BlogPostWithCustomData(models.Model):
    state = FSMField(default='new')

    @transition(field=state, source='new', target='published', conditions=[],
                custom={'label': 'Publish', 'type': '*'})
    def publish(self):
        pass

    @transition(field=state, source='published', target='destroyed',
                custom=dict(label="Destroy", type='manual'))
    def destroy(self):
        pass

    @transition(field=state, source='published', target='review',
                custom=dict(label="Periodic review", type='automated'))
    def review(self):
        pass

    class Meta:
        app_label = 'testapp'

@pytest.fixture()
def model():
    return BlogPostWithCustomData()



def test_initial_state(model):
    assert (model.state == 'new')
    transitions = list(model.get_available_state_transitions())
    assert len(transitions) == 1
    assert (transitions[0].target == 'published')
    assert (transitions[0].custom == {'label': 'Publish', 'type': '*'})

def test_all_transitions_have_custom_data(model):
    transitions = model.get_all_state_transitions()
    for t in transitions:
        assert (t.custom['label'])
        assert (t.custom['type'])

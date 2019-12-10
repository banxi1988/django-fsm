from django.db import models
from django.test import TestCase
from django_fsm_ex.decorators import transition
from django_fsm_ex.fields import FSMField


import pytest
pytestmark = pytest.mark.django_db

class BlogPostWithStringField(models.Model):
    state = FSMField(default='new')

    @transition(field='state', source='new', target='published', conditions=[])
    def publish(self):
        pass

    @transition(field='state', source='published', target='destroyed')
    def destroy(self):
        pass

    @transition(field='state', source='published', target='review')
    def review(self):
        pass

    class Meta:
        app_label = 'testapp'

@pytest.fixture()
def model():
  return BlogPostWithStringField()

def test_initial_state(model):
    assert (model.state == 'new')
    print(BlogPostWithStringField.state.field.model._meta.__dict__)
    model.publish()
    assert (model.state == 'published')

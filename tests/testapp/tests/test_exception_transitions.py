from django.db import models
from django.test import TestCase

from django_fsm_ex import can_proceed, transition, FSMField, post_transition

import pytest
pytestmark = pytest.mark.django_db

class ExceptionalBlogPost(models.Model):
    state = FSMField(default='new')

    @transition(field=state, source='new', target='published', on_error='crashed')
    def publish(self):
        raise Exception('Upss')

    @transition(field=state, source='new', target='deleted')
    def delete(self):
        raise Exception('Upss')

    class Meta:
        app_label = 'testapp'

@pytest.fixture()
def model():
    pass


class FSMFieldExceptionTest(TestCase):
    def setUp(self):
        self.model = ExceptionalBlogPost()
        post_transition.connect(self.on_post_transition, sender=ExceptionalBlogPost)
        self.post_transition_data = None

    def on_post_transition(self, **kwargs):
        self.post_transition_data = kwargs

    def test_state_changed_after_fail(self):
        assert (can_proceed(self.model.publish))
        pytest.raises(Exception, self.model.publish)
        assert (self.model.state == 'crashed')
        assert (self.post_transition_data['target'] == 'crashed')
        assert ('exception' in self.post_transition_data)

    def test_state_not_changed_after_fail(self):
        assert (can_proceed(self.model.delete))
        pytest.raises(Exception, self.model.delete)
        assert (self.model.state == 'new')
        assert (self.post_transition_data is None)

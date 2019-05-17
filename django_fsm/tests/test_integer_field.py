from django.db import models
from django_fsm.errors import TransitionNotAllowed
from django_fsm.decorators import transition
from django_fsm.fields import FSMIntegerField


import pytest
pytestmark = pytest.mark.django_db

class BlogPostStateEnum(object):
    NEW = 10
    PUBLISHED = 20
    HIDDEN = 30


class BlogPostWithIntegerField(models.Model):
    state = FSMIntegerField(default=BlogPostStateEnum.NEW)

    @transition(field=state, source=BlogPostStateEnum.NEW, target=BlogPostStateEnum.PUBLISHED)
    def publish(self):
        pass

    @transition(field=state, source=BlogPostStateEnum.PUBLISHED, target=BlogPostStateEnum.HIDDEN)
    def hide(self):
        pass

@pytest.fixture()
def model():
    return BlogPostWithIntegerField()

def test_known_transition_should_succeed(model):
    model.publish()
    assert (model.state == BlogPostStateEnum.PUBLISHED)

    model.hide()
    assert (model.state == BlogPostStateEnum.HIDDEN)

def test_unknow_transition_fails(model):
    pytest.raises(TransitionNotAllowed, model.hide)

from django.db import models
from django_fsm.decorators import transition
from django_fsm.fields import FSMField


class WorkflowMixin:
    @transition(field='state', source="*", target='draft')
    def draft(self):
        pass

    @transition(field='state', source="draft", target='published')
    def publish(self):
        pass

    class Meta:
        app_label = 'testapp'


class MixinSupportTestModel(WorkflowMixin, models.Model):
    state = FSMField(default="new")


def test_usecase():
    model = MixinSupportTestModel()

    model.draft()
    assert (model.state == 'draft')

    model.publish()
    assert (model.state == 'published')

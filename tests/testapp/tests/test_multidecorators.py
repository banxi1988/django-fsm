from django.db import models
from django_fsm_ex import transition, FSMField, post_transition


class DemoModel(models.Model):
    counter = models.IntegerField(default=0)
    signal_counter = models.IntegerField(default=0)
    state = FSMField(default="SUBMITTED_BY_USER")

    @transition(field=state, source="SUBMITTED_BY_USER", target="REVIEW_USER")
    @transition(field=state, source="SUBMITTED_BY_ADMIN", target="REVIEW_ADMIN")
    @transition(field=state, source="SUBMITTED_BY_ANONYMOUS", target="REVIEW_ANONYMOUS")
    def review(self):
        self.counter += 1

    class Meta:
        app_label = 'testapp'


def count_calls(sender, instance, name, source, target, **kwargs):
    instance.signal_counter += 1


post_transition.connect(count_calls, sender=DemoModel)


def test_transition_method_called_once():
    model = DemoModel()
    model.review()
    assert 1 == model.counter
    assert 1 == model.signal_counter

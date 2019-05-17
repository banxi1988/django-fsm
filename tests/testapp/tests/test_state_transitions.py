from django.db import models
from django_fsm.decorators import transition
from django_fsm.fields import FSMField

import pytest
pytestmark = pytest.mark.django_db


class Insect(models.Model):
    class STATE:
        CATERPILLAR = 'CTR'
        BUTTERFLY = 'BTF'

    STATE_CHOICES = ((STATE.CATERPILLAR, 'Caterpillar', 'Caterpillar'),
                     (STATE.BUTTERFLY, 'Butterfly', 'Butterfly'))

    state = FSMField(default=STATE.CATERPILLAR, state_choices=STATE_CHOICES)

    @transition(field=state, source=STATE.CATERPILLAR, target=STATE.BUTTERFLY)
    def cocoon(self):
        pass

    def fly(self):
        raise NotImplementedError

    def crawl(self):
        raise NotImplementedError

    class Meta:
        app_label = 'testapp'


class Caterpillar(Insect):
    def crawl(self):
        """
        Do crawl
        """

    class Meta:
        app_label = 'testapp'
        proxy = True


class Butterfly(Insect):
    def fly(self):
        """
        Do fly
        """

    class Meta:
        app_label = 'testapp'
        proxy = True


def test_initial_proxy_set_succeed():
    insect = Insect()
    assert (isinstance(insect, Caterpillar))

def test_transition_proxy_set_succeed():
    insect = Insect()
    insect.cocoon()
    assert (isinstance(insect, Butterfly))

def test_load_proxy_set():
    Insect.objects.create(state=Insect.STATE.CATERPILLAR)
    Insect.objects.create(state=Insect.STATE.BUTTERFLY)

    insects = Insect.objects.all()
    assert {Caterpillar, Butterfly} == set(insect.__class__ for insect in insects)

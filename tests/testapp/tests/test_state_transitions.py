from django.db import models
from django_fsm.decorators import transition
from django_fsm.errors import TransitionNotAllowed, InvalidResultState
from django_fsm.fields import FSMField

import pytest

from django_fsm.transition import get_fsm_meta, RETURN_VALUE, GET_STATE

pytestmark = pytest.mark.django_db


class Insect(models.Model):
    class STATE:
        CATERPILLAR = 'CTR'
        BUTTERFLY = 'BTF'
        BIRD = "BIRD"
    # state, title, proxy_cls_ref
    STATE_CHOICES = ((STATE.CATERPILLAR, 'Caterpillar', 'Caterpillar'),
                     (STATE.BUTTERFLY, 'Butterfly', 'Butterfly'),
                     (STATE.BIRD, 'bird', 'Bird')
                     )

    state = FSMField(default=STATE.CATERPILLAR, state_choices=STATE_CHOICES)

    @transition(field=state, source=STATE.CATERPILLAR, target=STATE.BUTTERFLY)
    def cocoon(self):
        pass

    @transition(field=state, source=STATE.BUTTERFLY, target=STATE.BIRD)
    def birdify(self):
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
    pytest.raises(LookupError,insect.birdify)

def test_load_proxy_set():
    Insect.objects.create(state=Insect.STATE.CATERPILLAR)
    Insect.objects.create(state=Insect.STATE.BUTTERFLY)

    insects = Insect.objects.all()
    assert {Caterpillar, Butterfly} == set(insect.__class__ for insect in insects)

def test_value_error_with_choice_and_state_choices():
    with pytest.raises(ValueError):
        class InvalieStatesModel(models.Model):
            class STATE:
                CATERPILLAR = 'CTR'
                BUTTERFLY = 'BTF'
                BIRD = "BIRD"

            # state, title, proxy_cls_ref
            STATE_CHOICES = ((STATE.CATERPILLAR, 'Caterpillar', 'Caterpillar'),
                             (STATE.BUTTERFLY, 'Butterfly', 'Butterfly'),
                             (STATE.BIRD, 'bird', 'Bird')
                             )

            state = FSMField(default=STATE.CATERPILLAR, choices=['CTR','BTF','BIRD'], state_choices=STATE_CHOICES)
            class Meta:
                app_label = "testapp"

def test_no_next_state():
    insect = Insect()
    fsm_meta = get_fsm_meta(insect.cocoon)
    pytest.raises(TransitionNotAllowed, fsm_meta.next_state,'not_a_state')
    pytest.raises(TransitionNotAllowed, fsm_meta.exception_state,'not_a_state')


def test_invalid_result_state():
    insect = Insect()
    ret_value = RETURN_VALUE("draft","online")
    get_value = GET_STATE(insect.cocoon, states=["draft","online"])
    pytest.raises(InvalidResultState,ret_value.get_state, insect,None,'not_a_state')
    # pytest.raises(InvalidResultState,get_value.get_state, insect,None,'not_a_state')

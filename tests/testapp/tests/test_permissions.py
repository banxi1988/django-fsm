from django.contrib.auth.models import User, Permission
from django.test import TestCase

from django_fsm.transition import has_transition_perm
from tests.testapp.models import BlogPost


class PermissionFSMFieldTest(TestCase):
    def setUp(self):
        self.model = BlogPost()
        self.unpriviledged = User.objects.create(username='unpriviledged')
        self.priviledged = User.objects.create(username='priviledged')
        self.staff = User.objects.create(username='staff', is_staff=True)

        self.priviledged.user_permissions.add(
            Permission.objects.get_by_natural_key('can_publish_post', 'testapp', 'blogpost'))
        self.priviledged.user_permissions.add(
            Permission.objects.get_by_natural_key('can_remove_post', 'testapp', 'blogpost'))

    def test_proviledged_access_succed(self):
        assert (has_transition_perm(self.model.publish, self.priviledged))
        assert (has_transition_perm(self.model.remove, self.priviledged))

        transitions = self.model.get_available_user_state_transitions(self.priviledged)
        assert ({'publish', 'remove', 'moderate'} ==
                set(transition.name for transition in transitions))

    def test_unpriviledged_access_prohibited(self):
        assert not (has_transition_perm(self.model.publish, self.unpriviledged))
        assert not (has_transition_perm(self.model.remove, self.unpriviledged))

        transitions = self.model.get_available_user_state_transitions(self.unpriviledged)
        assert ({'moderate'} == set(transition.name for transition in transitions))

    def test_permission_instance_method(self):
        assert not (has_transition_perm(self.model.restore, self.unpriviledged))
        assert (has_transition_perm(self.model.restore, self.staff))

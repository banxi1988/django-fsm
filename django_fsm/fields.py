# coding: utf-8
import inspect

from django.apps import apps
from django.db import models
from django.db.models.signals import class_prepared
from django.utils.functional import curry

from django_fsm.errors import TransitionNotAllowed
from django_fsm.signals import pre_transition, post_transition

__author__ = 'banxi'


def get_model(app_label, model_name):
    app = apps.get_app_config(app_label)
    return app.get_model(model_name)


def get_available_FIELD_transitions(instance, field):
    """
    List of transitions available in current model state
    with all conditions met
    """
    curr_state = field.get_state(instance)
    transitions = field.transitions[instance.__class__]

    for name, transition in transitions.items():
        meta = transition._django_fsm
        if meta.has_transition(curr_state) and meta.conditions_met(instance, curr_state):
            yield meta.get_transition(curr_state)


def get_all_FIELD_transitions(instance, field):
    """
    List of all transitions available in current model state
    """
    return field.get_all_transitions(instance.__class__)


def get_available_user_FIELD_transitions(instance, user, field):
    """
    List of transitions available in current model state
    with all conditions met and user have rights on it
    """
    for transition in get_available_FIELD_transitions(instance, field):
        if transition.has_perm(instance, user):
            yield transition


class FSMFieldDescriptor(object):
    def __init__(self, field):
        self.field = field

    def __get__(self, instance, type=None):
        if instance is None:
            return self
        return self.field.get_state(instance)

    def __set__(self, instance, value):
        if self.field.protected and self.field.name in instance.__dict__:
            raise AttributeError('Direct {0} modification is not allowed'.format(self.field.name))

        # Update state
        self.field.set_proxy(instance, value)
        self.field.set_state(instance, value)


class FSMFieldMixin(object):
    descriptor_class = FSMFieldDescriptor

    def __init__(self, *args, **kwargs):
        self.protected = kwargs.pop('protected', False)
        self.transitions = {}  # cls -> (transitions name -> method)
        self.state_proxy = {}  # state -> ProxyClsRef

        state_choices = kwargs.pop('state_choices', None)
        choices = kwargs.get('choices', None)
        if state_choices is not None and choices is not None:
            raise ValueError('Use one of choices or state_choices value')

        if state_choices is not None:
            choices = []
            for state, title, proxy_cls_ref in state_choices:
                choices.append((state, title))
                self.state_proxy[state] = proxy_cls_ref
            kwargs['choices'] = choices

        super(FSMFieldMixin, self).__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super(FSMFieldMixin, self).deconstruct()
        if self.protected:
            kwargs['protected'] = self.protected
        return name, path, args, kwargs

    def get_state(self, instance):
        return instance.__dict__[self.name]

    def set_state(self, instance, state):
        instance.__dict__[self.name] = state

    def set_proxy(self, instance, state):
        """
        Change class
        """
        if state in self.state_proxy:
            state_proxy = self.state_proxy[state]

            try:
                app_label, model_name = state_proxy.split(".")
            except ValueError:
                # If we can't split, assume a model in current app
                app_label = instance._meta.app_label
                model_name = state_proxy

            model = get_model(app_label, model_name)
            if model is None:
                raise ValueError('No model found {0}'.format(state_proxy))

            instance.__class__ = model

    def change_state(self, instance, method, *args, **kwargs):
        meta = method._django_fsm
        method_name = method.__name__
        current_state = self.get_state(instance)

        if not meta.has_transition(current_state):
            raise TransitionNotAllowed(
                "Can't switch from state '{0}' using method '{1}'".format(current_state, method_name),
                object=instance, method=method)
        if not meta.conditions_met(instance, current_state):
            raise TransitionNotAllowed(
                "Transition conditions have not been met for method '{0}'".format(method_name),
                object=instance, method=method)

        next_state = meta.next_state(current_state)

        signal_kwargs = {
            'sender': instance.__class__,
            'instance': instance,
            'name': method_name,
            'field': meta.field,
            'source': current_state,
            'target': next_state,
            'method_args' : args,
            'method_kwargs' : kwargs
        }

        pre_transition.send(**signal_kwargs)

        try:
            result = method(instance, *args, **kwargs)
            if next_state is not None:
                if hasattr(next_state, 'get_state'):
                    from django_fsm.transition import transition
                    next_state = next_state.get_state(
                        instance, transition, result,
                        args=args, kwargs=kwargs)
                    signal_kwargs['target'] = next_state
                self.set_proxy(instance, next_state)
                self.set_state(instance, next_state)
        except Exception as exc:
            exception_state = meta.exception_state(current_state)
            if exception_state:
                self.set_proxy(instance, exception_state)
                self.set_state(instance, exception_state)
                signal_kwargs['target'] = exception_state
                signal_kwargs['exception'] = exc
                post_transition.send(**signal_kwargs)
            raise
        else:
            post_transition.send(**signal_kwargs)

        return result

    def get_all_transitions(self, instance_cls):
        """
        Returns [(source, target, name, method)] for all field transitions
        """
        transitions = self.transitions[instance_cls]

        for name, transition in transitions.items():
            meta = transition._django_fsm

            for transition in meta.transitions.values():
                yield transition

    def contribute_to_class(self, cls, name, **kwargs):
        self.base_cls = cls

        super(FSMFieldMixin, self).contribute_to_class(cls, name, **kwargs)
        setattr(cls, self.name, self.descriptor_class(self))
        setattr(cls, 'get_all_{0}_transitions'.format(self.name),
                curry(get_all_FIELD_transitions, field=self))
        setattr(cls, 'get_available_{0}_transitions'.format(self.name),
                curry(get_available_FIELD_transitions, field=self))
        setattr(cls, 'get_available_user_{0}_transitions'.format(self.name),
                curry(get_available_user_FIELD_transitions, field=self))

        class_prepared.connect(self._collect_transitions)

    def _collect_transitions(self, *args, **kwargs):
        sender = kwargs['sender']

        if not issubclass(sender, self.base_cls):
            return

        def is_field_transition_method(attr):
            return (inspect.ismethod(attr) or inspect.isfunction(attr)) \
                and hasattr(attr, '_django_fsm') \
                and attr._django_fsm.field in [self, self.name]

        sender_transitions = {}
        transitions = inspect.getmembers(sender, predicate=is_field_transition_method)
        for method_name, method in transitions:
            method._django_fsm.field = self
            sender_transitions[method_name] = method

        self.transitions[sender] = sender_transitions


class FSMField(FSMFieldMixin, models.CharField):
    """
    State Machine support for Django model as CharField
    """
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('max_length', 50)
        super(FSMField, self).__init__(*args, **kwargs)


class FSMIntegerField(FSMFieldMixin, models.IntegerField):
    """
    Same as FSMField, but stores the state value in an IntegerField.
    """
    pass


class FSMKeyField(FSMFieldMixin, models.ForeignKey):
    """
    State Machine support for Django model
    """
    def get_state(self, instance):
        return instance.__dict__[self.attname]

    def set_state(self, instance, state):
        instance.__dict__[self.attname] = self.to_python(state)
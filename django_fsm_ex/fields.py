# coding: utf-8
import inspect
from typing import Type, TYPE_CHECKING, Optional

from django.apps import apps
from django.db import models
from django.db.models import Model
from django.db.models.signals import class_prepared
from functools import partialmethod

from django_fsm_ex.errors import TransitionNotAllowed
from django_fsm_ex.signals import pre_transition, post_transition, transition_not_allowed, no_transition
from django_fsm_ex.types import StateType, TransitionPermission, OptStateType, OptTransitionConditions, \
    OptTransitionPermission, OptDict

if TYPE_CHECKING:
    from django.contrib.auth.models import User

__author__ = 'banxi'

__all__ = ['Transition','FSMFieldMixin','FSMFieldType', 'FSMField', 'FSMIntegerField','FSMKeyField','get_all_FIELD_transitions', 'get_available_FIELD_transitions', 'get_available_user_FIELD_transitions','FSMMeta','get_fsm_meta']

class Transition:
    def __init__(self, method,
                 source: StateType,
                 target: StateType,
                 on_error: Optional[StateType],
                 conditions:list,
                 permission: TransitionPermission,
                 custom:dict):
        """

        :param method:  应用了 transition 装饰的  django.Model 实例方法
        :param source: 原状态,可以是单个状态也可以是一系列状态
        :param target:  目标状态
        :param on_error:  出错时设置的状态
        :param conditions:
        :param permission: 执行状态转换方法所需要的权限,或者是一个接收 instance,user 参数的回调函数 。
        :param custom: 其他自定义参数。
        """
        self.method = method
        self.source = source
        self.target = target
        self.on_error = on_error
        self.conditions = conditions
        self.permission = permission
        self.custom = custom

    @property
    def name(self):
        return self.method.__name__

    def has_perm(self, instance:Model, user:'User'):
        if not self.permission:
            return True
        elif callable(self.permission):
            return bool(self.permission(instance, user))
        elif user.has_perm(self.permission, instance):
            return True
        elif user.has_perm(self.permission):
            return True
        else:
            return False


class FSMFieldDescriptor:
    def __init__(self, field):
        self.field :FSMFieldType = field

    def __get__(self, instance:Model, instancetype=None):
        if instance is None:
            return self
        return self.field.get_state(instance)

    def __set__(self, instance:Model, value):
        if self.field.protected and self.field.name in instance.__dict__:
            meta = self.field.model._meta
            raise AttributeError(f'不允许直接修改{meta.verbose_name}的{self.field.verbose_name}')

        # Update state
        self.field._do_update_state(instance,value)

def _fmt_field_label(field:models.Field):
    model = getattr(field,'model',None)
    if model:
        model_label = field.model._meta.verbose_name
        field_label = field.verbose_name
        return f'{model_label}的{field_label}'
    else:
        # 初始状态时 Field 还没有绑定到 Model, 但是 transition 是在创建绑定 Model 之前进行的
        # 如果重复定义时此时没有 model
        return field.verbose_name

class FSMFieldMixin:
    descriptor_class = FSMFieldDescriptor

    def __init__(self, *args, **kwargs):
        self.protected = kwargs.pop('protected', False)
        self.transitions = {}  # cls -> (transitions name -> method)
        self.state_proxy = {}  # state -> ProxyClsRef

        state_choices = kwargs.pop('state_choices', None)
        choices = kwargs.get('choices', None)
        if state_choices is not None and choices is not None:
            raise ValueError('不要同时设置choices 和 state_choices')

        if state_choices is not None:
            choices = []
            for state, title, proxy_cls_ref in state_choices:
                choices.append((state, title))
                self.state_proxy[state] = proxy_cls_ref
            kwargs['choices'] = choices

        super(FSMFieldMixin, self).__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        if self.protected:
            kwargs['protected'] = self.protected
        return name, path, args, kwargs

    def get_state(self, instance:Model):
        return instance.__dict__[self.name]

    def _do_update_state(self,instance,state):
        self.set_state(instance,state)
        self.set_proxy(instance,state)

    def set_state(self, instance:Model, state):
        instance.__dict__[self.name] = state

    def set_proxy(self, instance:Model, state):
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
            model = apps.get_model(app_label, model_name)
            # if not model found will raise LookupError
            instance.__class__ = model

    def change_state(self, instance:Model, method, *args, **kwargs):
        meta = get_fsm_meta(method)
        method_name = method.__name__
        current_state = self.get_state(instance)
        field = meta.field
        method_label = getattr(method,'label',method_name)
        state_label = getattr(current_state,'label', str(current_state))
        field_label = _fmt_field_label(field)
        signal_kwargs = {
            'sender': instance.__class__,
            'instance': instance,
            'name': method_name,
            'field': field,
            'source': current_state,
            'method_args' : args,
            'method_kwargs' : kwargs
        }
        if not meta.has_transition(current_state):
            error_msg = f"{field_label}当前处于{state_label}状态,不能进行{method_label}操作"
            no_transition.send(**signal_kwargs)
            raise TransitionNotAllowed(error_msg, object=instance, method=method,field=field,current_state=current_state)

        next_state = meta.next_state(current_state)
        signal_kwargs['target'] = next_state
        if not meta.conditions_met(instance, current_state):
            error_msg = f"{field_label}当前处于{state_label}状态,尚未满足进行{method_label}操作的条件"
            transition_not_allowed.send(**signal_kwargs)
            raise TransitionNotAllowed(error_msg, object=instance, method=method,field=field,current_state=current_state)

        pre_transition.send(**signal_kwargs)

        try:
            result = method(instance, *args, **kwargs)
            if next_state is not None:
                if hasattr(next_state, 'get_state'):
                    from django_fsm_ex.decorators import transition
                    next_state = next_state.get_state(
                        instance, transition, result,
                        args=args, kwargs=kwargs)
                    signal_kwargs['target'] = next_state
                self._do_update_state(instance, next_state)
        except Exception as exc:
            exception_state = meta.exception_state(current_state)
            if exception_state:
                self._do_update_state(instance, exception_state)
                signal_kwargs['target'] = exception_state
                signal_kwargs['exception'] = exc
                post_transition.send(**signal_kwargs)
            raise
        else:
            post_transition.send(**signal_kwargs)

        return result

    def get_all_transitions(self, instance_cls:Type[Model]):
        """
        Returns [(source, target, name, method)] for all field transitions
        """
        transitions = self.transitions[instance_cls]

        for name, transition in transitions.items():
            meta = get_fsm_meta(transition)

            for transition in meta.state_to_transition.values():
                yield transition

    def contribute_to_class(self, cls, name, **kwargs):
        self.base_cls = cls
        super(FSMFieldMixin, self).contribute_to_class(cls, name, **kwargs)
        field_name = self.name
        setattr(cls, field_name, self.descriptor_class(self))
        setattr(cls, f'get_all_{field_name}_transitions', partialmethod(get_all_FIELD_transitions, field=self))
        setattr(cls, f'get_available_{field_name}_transitions',
                partialmethod(get_available_FIELD_transitions, field=self))
        setattr(cls, f'get_available_user_{field_name}_transitions',
                partialmethod(get_available_user_FIELD_transitions, field=self))

        class_prepared.connect(self._collect_transitions)

    def _collect_transitions(self, *args, **kwargs):

        sender = kwargs['sender']

        if not issubclass(sender, self.base_cls):
            return

        def is_field_transition_method(attr):
            if inspect.ismethod(attr) or inspect.isfunction(attr):
                try:
                    fsm_meta = get_fsm_meta(attr)
                except TypeError:
                    return  False
                else:
                    return fsm_meta.field in [self, self.name]
            return  False

        sender_transitions = {}
        transitions = inspect.getmembers(sender, predicate=is_field_transition_method)
        for method_name, method in transitions:
            meta = get_fsm_meta(method)
            meta.field = self
            sender_transitions[method_name] = method

        self.transitions[sender] = sender_transitions

class FSMFieldType(FSMFieldMixin, models.Field):
    pass

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
    def get_state(self, instance:Model):
        return instance.__dict__[self.attname]

    def set_state(self, instance:Model, state):
        instance.__dict__[self.attname] = self.to_python(state)

def get_available_FIELD_transitions(instance:Model, field:FSMFieldType):
    """
    List of transitions available in current model state
    with all conditions met
    """
    curr_state = field.get_state(instance)
    transitions = field.transitions[instance.__class__]

    for name, transition in transitions.items():
        meta = get_fsm_meta(transition)
        if meta.has_transition(curr_state) and meta.conditions_met(instance, curr_state):
            yield meta.get_transition(curr_state)


def get_all_FIELD_transitions(instance:Model, field:FSMFieldType):
    """
    List of all transitions available in current model state
    """
    return field.get_all_transitions(instance.__class__)


def get_available_user_FIELD_transitions(instance:Model, user:'User', field:FSMFieldType):
    """
    List of transitions available in current model state
    with all conditions met and user have rights on it
    """
    for transition in get_available_FIELD_transitions(instance, field):
        if transition.has_perm(instance, user):
            yield transition


class FSMMeta:
    """
    封装状态转移函数信息

    Models methods transitions meta information
    """
    def __init__(self, field:FSMFieldType, method):
        self.field = field
        self.state_to_transition = {}  # source -> Transition

    def get_transition(self, source:StateType):
        transition = self.state_to_transition.get(source, None)
        if transition is None:
            transition = self.state_to_transition.get('*', None)
        if transition is None:
            transition = self.state_to_transition.get('+', None)
        return transition

    def add_transition(self, method, source:StateType, target:StateType, on_error:OptStateType=None, conditions:OptTransitionConditions=None, permission:OptTransitionPermission=None, custom:OptDict=None):
        if custom is None:
            custom = {}
        if conditions is None:
            conditions = []
        if source in self.state_to_transition:
            source_label = getattr(source,'label', str(source))
            field_label = _fmt_field_label(self.field)
            raise AssertionError(f'{field_label}不允许重复定义{source_label}状态的转移函数')
        self.state_to_transition[source] = Transition(
            method=method,
            source=source,
            target=target,
            on_error=on_error,
            conditions=conditions,
            permission=permission,
            custom=custom)

    def has_transition(self, state:StateType):
        """
        Lookup if any transition exists from current model state using current method
        """
        if state in self.state_to_transition:
            return True

        if '*' in self.state_to_transition:
            return True

        if '+' in self.state_to_transition and self.state_to_transition['+'].target != state:
            return True

        return False

    def conditions_met(self, instance:Model, state:StateType):
        """
        Check if all conditions have been met
        """
        transition = self.get_transition(state)

        if transition is None:
            return False
        elif not transition.conditions:
            return True
        else:
            # return all(map(lambda condition: condition(instance), transition.conditions))
            return  all(condition(instance) for condition in transition.conditions)

    def has_transition_perm(self, instance:Model, state:StateType, user:'User'):
        transition = self.get_transition(state)

        if not transition:
            return False
        else:
            return transition.has_perm(instance, user)

    def next_state(self, current_state:StateType):
        transition = self.get_transition(current_state)

        if transition is None:
            self._fail_no_transition(current_state)

        return transition.target

    def _fail_no_transition(self,current_state:StateType):
        state_label = getattr(current_state, 'label', str(current_state))
        field_label = _fmt_field_label(self.field)
        raise TransitionNotAllowed(f'{field_label}当前状态({state_label})没有可转移的状态')

    def exception_state(self, current_state:StateType):
        transition = self.get_transition(current_state)

        if transition is None:
          self._fail_no_transition(current_state)

        return transition.on_error


def get_fsm_meta(method) -> FSMMeta:
    from django_fsm_ex.decorators import FSM_META_ATTR_NAME
    try:
        meta = getattr(method, FSM_META_ATTR_NAME)
    except AttributeError:
        if inspect.isfunction(method):
            func_name = method.__name__
        else:
            func = getattr(method, '__func__')
            func_name = func.__name__
        raise TypeError(f'{func_name} method is not transition')
    else:
        return meta


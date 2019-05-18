# coding: utf-8
import inspect
import abc

from django.contrib.auth.models import User
from django.db.models import Model

from django_fsm.errors import TransitionNotAllowed, InvalidResultState, ConcurrentTransition
from django_fsm.types import ChangeStatePermission, StateType, OptList, OptDict

__author__ = 'banxi'




class Transition:
    def __init__(self, method,
                 source: StateType,
                 target: StateType,
                 on_error,
                 conditions:list,
                 permission: ChangeStatePermission,
                 custom:dict):
        """

        :param method:  应用了 transition 装饰的  django.Model 实例方法
        :param source: 原状态,可以是单个状态也可以是一系列状态
        :param target:  目标状态
        :param on_error:  出错的回调
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

    def has_perm(self, instance:Model, user:User):
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


class FSMMeta:
    """
    Models methods transitions meta information
    """
    def __init__(self, field, method):
        self.field = field
        self.state_to_transition = {}  # source -> Transition

    def get_transition(self, source):
        transition = self.state_to_transition.get(source, None)
        if transition is None:
            transition = self.state_to_transition.get('*', None)
        if transition is None:
            transition = self.state_to_transition.get('+', None)
        return transition

    def add_transition(self, method, source, target, on_error=None, conditions=None, permission=None, custom=None):
        if custom is None:
            custom = {}
        if conditions is None:
            conditions = []
        if source in self.state_to_transition:
            raise AssertionError('Duplicate transition for {0} state'.format(source))
        self.state_to_transition[source] = Transition(
            method=method,
            source=source,
            target=target,
            on_error=on_error,
            conditions=conditions,
            permission=permission,
            custom=custom)

    def has_transition(self, state):
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

    def conditions_met(self, instance, state):
        """
        Check if all conditions have been met
        """
        transition = self.get_transition(state)

        if transition is None:
            return False
        elif not transition.conditions:
            return True
        else:
            return all(map(lambda condition: condition(instance), transition.conditions))

    def has_transition_perm(self, instance, state, user):
        transition = self.get_transition(state)

        if not transition:
            return False
        else:
            return transition.has_perm(instance, user)

    def next_state(self, current_state):
        transition = self.get_transition(current_state)

        if transition is None:
            raise TransitionNotAllowed(f'No transition from {current_state}')

        return transition.target

    def exception_state(self, current_state):
        transition = self.get_transition(current_state)

        if transition is None:
            raise TransitionNotAllowed(f'No transition from {current_state}')

        return transition.on_error


class ConcurrentTransitionMixin:
    """
    Protects a Model from undesirable effects caused by concurrently executed transitions,
    e.g. running the same transition multiple times at the same time, or running different
    transitions with the same SOURCE state at the same time.

    This behavior is achieved using an idea based on optimistic locking. No additional
    version field is required though; only the state field(s) is/are used for the tracking.
    This scheme is not that strict as true *optimistic locking* mechanism, it is however
    more lightweight - leveraging the specifics of FSM models.

    Instance of a model based on this Mixin will be prevented from saving into DB if any
    of its state fields (instances of FSMFieldMixin) has been changed since the object
    was fetched from the database. *ConcurrentTransition* exception will be raised in such
    cases.

    For guaranteed protection against such race conditions, make sure:
    * Your transitions do not have any side effects except for changes in the database,
    * You always run the save() method on the object within django.db.transaction.atomic()
    block.

    Following these recommendations, you can rely on ConcurrentTransitionMixin to cause
    a rollback of all the changes that have been executed in an inconsistent (out of sync)
    state, thus practically negating their effect.
    """
    def __init__(self, *args, **kwargs):
        super(ConcurrentTransitionMixin, self).__init__(*args, **kwargs)
        self._update_initial_state()

    @property
    def state_fields(self):
        from django_fsm.fields import FSMFieldMixin
        return filter(
            lambda field: isinstance(field, FSMFieldMixin),
            self._meta.fields
        )

    def _do_update(self, base_qs, using, pk_val, values, update_fields, forced_update):
        # _do_update is called once for each model class in the inheritance hierarchy.
        # We can only filter the base_qs on state fields (can be more than one!) present in this particular model.

        # Select state fields to filter on
        filter_on = filter(lambda field: field.model == base_qs.model, self.state_fields)

        # state filter will be used to narrow down the standard filter checking only PK
        state_filter = dict((field.attname, self.__initial_states[field.attname]) for field in filter_on)

        updated = super(ConcurrentTransitionMixin, self)._do_update(
            base_qs=base_qs.filter(**state_filter),
            using=using,
            pk_val=pk_val,
            values=values,
            update_fields=update_fields,
            forced_update=forced_update
        )

        # It may happen that nothing was updated in the original _do_update method not because of unmatching state,
        # but because of missing PK. This codepath is possible when saving a new model instance with *preset PK*.
        # In this case Django does not know it has to do INSERT operation, so it tries UPDATE first and falls back to
        # INSERT if UPDATE fails.
        # Thus, we need to make sure we only catch the case when the object *is* in the DB, but with changed state; and
        # mimic standard _do_update behavior otherwise. Django will pick it up and execute _do_insert.
        if not updated and base_qs.filter(pk=pk_val).exists():
            raise ConcurrentTransition("Cannot save object! The state has been changed since fetched from the database!")

        return updated

    def _update_initial_state(self):
        self.__initial_states = dict(
            (field.attname, field.value_from_object(self)) for field in self.state_fields
        )

    def save(self, *args, **kwargs):
        super(ConcurrentTransitionMixin, self).save(*args, **kwargs)
        self._update_initial_state()

def get_fsm_meta(method) -> FSMMeta:
    from django_fsm.decorators import FSM_META_ATTR_NAME
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

def can_proceed(bound_method, check_conditions=True):
    """
    Returns True if model in state allows to call bound_method

    Set ``check_conditions`` argument to ``False`` to skip checking
    conditions.
    """
    meta = get_fsm_meta(bound_method)
    instance = getattr(bound_method, '__self__')
    current_state = meta.field.get_state(instance)

    return meta.has_transition(current_state) and (
    not check_conditions or meta.conditions_met(instance, current_state))


def has_transition_perm(bound_method, user):
    """
    Returns True if model in state allows to call bound_method and user have rights on it
    """
    meta = get_fsm_meta(bound_method)
    instance = getattr(bound_method, '__self__')
    current_state = meta.field.get_state(instance)

    return (meta.has_transition(current_state) and
            meta.conditions_met(instance, current_state) and
            meta.has_transition_perm(instance, current_state, user))


class State(abc.ABC):
    @abc.abstractmethod
    def get_state(self, model, transition, result,args:OptList=None, kwargs:OptDict=None):
      pass # pragma no cover


class RETURN_VALUE(State):
    def __init__(self, *allowed_states):
        self.allowed_states = allowed_states if allowed_states else None

    def get_state(self, model, transition, result,args:OptList=None, kwargs:OptDict=None):
        if self.allowed_states is not None:
            if result not in self.allowed_states:
                raise InvalidResultState(
                    f'{result} is not in list of allowed states\n{self.allowed_states}')
        return result


class GET_STATE(State):
    def __init__(self, func, states=None):
        self.func = func
        self.allowed_states = states

    def get_state(self, model, transition, result, args:OptList=None, kwargs:OptDict=None):
        if args is None:
            args = [] # pragma no cover
        if kwargs is None:
            kwargs = {} # pragma no cover
        result_state = self.func(model, *args, **kwargs)
        if self.allowed_states is not None:
            if result_state not in self.allowed_states:
                raise InvalidResultState(
                    f'{result} is not in list of allowed states\n{self.allowed_states}')
        return result_state
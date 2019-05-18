# coding: utf-8
from functools import wraps
from typing import Optional, Union, Iterable

from django.db import models
from django.db.models import Model

from django_fsm.types import StateType, ChangeStatePermission

__author__ = 'banxi'

FSM_META_ATTR_NAME = '_django_fsm'
"""
添加在 Django Model 实例方法对象中隐藏属性。
"""


def transition(field:models.Field,
               source:StateType='*',
               target:Optional[Union[StateType,Iterable[StateType]]]=None,
               on_error=None,
               conditions:Optional[list]=None,
               permission:Optional[ChangeStatePermission]=None,
               custom:Optional[dict]=None):
    """
    Method decorator for mark allowed transitions

    Set target to None if current state needs to be validated and
    has not changed after the function call

    带参数的装饰器函数

    :return:
    """
    from django_fsm.transition import FSMMeta

    def inner_transition(func):
        wrapper_installed, fsm_meta = True, getattr(func,  FSM_META_ATTR_NAME, None)
        if not fsm_meta:
            wrapper_installed = False
            fsm_meta = FSMMeta(field=field, method=func)
            setattr(func, FSM_META_ATTR_NAME, fsm_meta)
        if isinstance(source, (list, tuple, set)):
            iter_sources = source
        else:
            iter_sources = [source]
        for state in iter_sources:
            fsm_meta.add_transition(func, state, target, on_error, conditions, permission, custom)

        @wraps(func)
        def _change_state(instance:Model, *args, **kwargs):
            return fsm_meta.field.change_state(instance, func, *args, **kwargs)

        if not wrapper_installed:
            return _change_state

        return func

    return inner_transition
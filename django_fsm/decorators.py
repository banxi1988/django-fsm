# coding: utf-8
from functools import wraps
from typing import Optional, Union, Iterable

from django.db.models import Model

from django_fsm.fields import  FSMFieldType
from django_fsm.types import StateType, ChangeStatePermission

__author__ = 'banxi'

_FSM_META_ATTR_NAME_PREFIX = '_django_fsm'

def get_fsm_meta_attr_name(*,field_name:str):
    """为了支持同一个方法绑定不同状态字段的 transition ,attr_name 改为加入关联 field"""
    return f"{_FSM_META_ATTR_NAME_PREFIX}_{field_name}"

"""
添加在 Django Model 实例方法对象中隐藏属性。
"""


def transition(field:Union[FSMFieldType,str],
               source:StateType='*',
               target:Optional=None,
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
        field_name = field if isinstance(field,str) else field.name
        attr_name = get_fsm_meta_attr_name(field_name=field_name)
        wrapper_installed, fsm_meta = True, getattr(func,  attr_name, None)
        if not fsm_meta:
            wrapper_installed = False
            fsm_meta = FSMMeta(field_or_name=field, method=func)
            setattr(func, attr_name, fsm_meta)
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
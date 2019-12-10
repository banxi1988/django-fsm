# coding: utf-8
from typing import Union, Callable, List, Dict, Optional, Iterable,TYPE_CHECKING
from django.db.models import Model

if TYPE_CHECKING:
  from django.contrib.auth.models import User

__author__ = 'banxi'

TransitionPermission = Union[Callable[[Model, 'User'], bool], str]
"""状态转移需要的权限,可以是一个回调函数也可以是权限"""
OptTransitionPermission = Optional[TransitionPermission]

TransitionCondition = Callable[[Model], bool]
"""状态转移条件判断函数"""
TransitionConditions = Iterable[TransitionCondition]
OptTransitionConditions = Optional[TransitionConditions]
StateType = Union[str,int]
OptStateType = Optional[StateType]

OptList = Union[List,None]
OptDict = Union[Dict,None]

# coding: utf-8
from typing import Union, Callable, List, Dict

from django.contrib.auth.models import User
from django.db.models import Model

__author__ = 'banxi'

ChangeStatePermission = Union[Callable[[Model, User], bool], str]
"""状态转移需要的权限,可以是一个回调函数也可以是权限"""

StateType = Union[str,int]
"""状态转移需要的权限,可以是一个回调函数也可以是权限"""

OptList = Union[List,None]
OptDict = Union[Dict,None]

# coding: utf-8
from types import FunctionType
from typing import List

from django.apps import AppConfig

__author__ = '代码会说话'

_fsm_meta_transition_register_queue:List[FunctionType] = []

class FsmAppConfig(AppConfig):
  name = "django_fsm"
  label = "django_fsm"

  def ready(self):
    for func in _fsm_meta_transition_register_queue:
      func()
    _fsm_meta_transition_register_queue.clear()


# coding: utf-8
from django.dispatch import Signal

__all__ = [
  'pre_transition',
  'post_transition',
  'transition_not_allowed',
  'no_transition'
]

pre_transition = Signal(providing_args=['instance', 'name','field', 'source', 'target'])
post_transition = Signal(providing_args=['instance', 'name','field', 'source', 'target', 'exception'])
transition_not_allowed = Signal(providing_args=['instance', 'name','field', 'source', 'target'])
no_transition = Signal(providing_args=['instance', 'name','field', 'source'])

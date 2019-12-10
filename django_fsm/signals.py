# coding: utf-8
from django.dispatch import Signal

pre_transition = Signal(providing_args=['instance', 'name','field', 'source', 'target'])
post_transition = Signal(providing_args=['instance', 'name','field', 'source', 'target', 'exception'])
transition_not_allowed = Signal(providing_args=['instance', 'name','field', 'source', 'target'])
no_transition = Signal(providing_args=['instance', 'name','field', 'source'])

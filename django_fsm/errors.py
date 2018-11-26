# coding: utf-8

__author__ = 'banxi'

class FSMException(Exception):
    pass

class TransitionNotAllowed(FSMException):
    """Raised when a transition is not allowed"""

    def __init__(self, *args, **kwargs):
        self.object = kwargs.pop('object', None)
        self.method = kwargs.pop('method', None)
        super(TransitionNotAllowed, self).__init__(*args, **kwargs)


class InvalidResultState(FSMException):
    """Raised when we got invalid result state"""


class ConcurrentTransition(FSMException):
    """
    Raised when the transition cannot be executed because the
    object has become stale (state has been changed since it
    was fetched from the database).
    """
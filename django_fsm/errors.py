# coding: utf-8

__author__ = 'banxi'

class FSMException(Exception):
    pass

class TransitionNotAllowed(FSMException):
    """
    Raised when a transition is not allowed
    当不支持对应的状态转换时抛出此异常
    """

    def __init__(self, *args, **kwargs):
        self.object = kwargs.pop('object', None)
        self.method = kwargs.pop('method', None)
        super().__init__(*args, **kwargs)


class InvalidResultState(FSMException):
    """
    Raised when we got invalid result state
    当得到的结果状态非法时抛出的异常
    """


class ConcurrentTransition(FSMException):
    """
    Raised when the transition cannot be executed because the
    object has become stale (state has been changed since it
    was fetched from the database).
    当对象已经过期，抛出的异常（也许是因为从数据库读取回来新的状态，可能是其他实例修改了此状态。）
    """
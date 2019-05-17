#!/usr/bin/env python3
import os
import sys
import pytest


if __name__ == '__main__':
    os.environ['DJANGO_SETTINGS_MODULE'] = 'tests.settings'
    sys.exit(pytest.main(args=['--cov', 'django_fsm']))

# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

# pylint: skip-file

from pytest import fixture
from cache import Cache


@fixture
def cls():
    return Cache()


def test_add(cls):
    cls.add('my_key', 'my_value')
    assert cls.get('my_key') == 'my_value'


def test_exists(cls):
    cls.add('my_key', 'my_value')
    cls.add('false_key', False)
    assert cls.exists('my_key') is True
    assert cls.exists('false_key') is True
    assert cls.exists('missing_key') is False


def test_get(cls):
    cls.add('my_key', 'my_value')
    cls.add('true_key', True)
    cls.add('false_key', False)
    assert cls.get('my_key') == 'my_value'
    assert cls.get('true_key') is True
    assert cls.get('false_key') is False

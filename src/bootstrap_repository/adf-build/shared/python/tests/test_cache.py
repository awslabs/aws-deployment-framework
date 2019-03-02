# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

# pylint: skip-file

from pytest import fixture
from cache import Cache


@fixture
def cls():
    return Cache()


def test_add(cls):
    cls.add('my_key', 'my_value')


def test_check(cls):
    cls.add('my_key', 'my_value')
    assert cls.check('my_key') == 'my_value'

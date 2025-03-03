# Copyright Amazon.com Inc. or its affiliates.
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


def test_remove_existing_key(cls):
    # Arrange
    cls.add("test_key", "test_value")

    # Act
    cls.remove("test_key")

    # Assert
    assert cls.exists("test_key") is False
    assert cls.get("test_key") is None


def test_remove_non_existing_key(cls):
    # Arrange
    cls.remove("non_existing_key")

    # Assert
    assert cls.exists("non_existing_key") is False
    assert cls.get("non_existing_key") is None


def test_remove_and_read(cls):
    # Arrange
    cls.add("test_key", "test_value")

    # Act
    cls.remove("test_key")
    cls.add("test_key", "new_value")

    # Assert
    assert cls.exists("test_key") is True
    assert cls.get("test_key") == "new_value"


def test_remove_multiple_keys(cls):
    # Arrange
    cls.add("key1", "value1")
    cls.add("key2", "value2")

    # Act
    cls.remove("key1")

    # Assert
    assert cls.exists("key1") is False
    assert cls.exists("key2") is True
    assert cls.get("key1") is None
    assert cls.get("key2") == "value2"

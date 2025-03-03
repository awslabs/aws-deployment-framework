# Copyright Amazon.com Inc. or its affiliates.
# SPDX-License-Identifier: MIT-0

# pylint: skip-file

from pytest import fixture, mark, raises
from stubs import stub_parameter_store
from mock import Mock

from cache import Cache
from errors import ParameterNotFoundError
from parameter_store import ParameterStore


@fixture
def mock_ssm_client():
    ssm_client = Mock()
    ssm_client.exceptions.ParameterNotFound = Exception
    return ssm_client


@fixture
def mock_role(mock_ssm_client):
    role = Mock()
    role.client.return_value = mock_ssm_client
    return role


@fixture
def cache():
    return Cache()


@fixture
def cls(mock_role, cache):
    cls = ParameterStore("us-east-1", mock_role, cache)
    return cls


@mark.parametrize(
    "input_name, output_path",
    [
        ("/adf/test", "/adf/test"),
        ("adf/test", "/adf/test"),
        ("/adf_version", "/adf_version"),
        ("/test", "/test"),
        ("test", "/test"),
        ("/other/test", "/other/test"),
        ("other/test", "/other/test"),
    ],
)
def test_build_param_name_not_adf_only(input_name, output_path):
    assert (
        ParameterStore._build_param_name(
            input_name,
            adf_only=False,
        )
        == output_path
    )


@mark.parametrize(
    "input_name, output_path",
    [
        ("/adf/test", "/adf/test"),
        ("adf/test", "/adf/test"),
        ("/adf_version", "/adf/adf_version"),
        ("/test", "/adf/test"),
        ("test", "/adf/test"),
        ("/other/test", "/adf/other/test"),
        ("other/test", "/adf/other/test"),
    ],
)
def test_build_param_name_adf_only(input_name, output_path):
    assert ParameterStore._build_param_name(input_name) == output_path


def test_fetch_parameter(cls):
    cls.client = Mock()
    cls.client.get_parameter.return_value = stub_parameter_store.get_parameter
    assert cls.fetch_parameter("some_path") == "some_parameter_value"


def test_has_cache(cls):
    assert cls.cache is not None


def test_put_parameter_updates_cache(cls, mock_ssm_client):
    # Arrange
    parameter_name = "test-param"
    expected_value = "test-value"
    full_param_name = f"/adf/{parameter_name}"

    # Simulate parameter not found to trigger put
    mock_ssm_client.get_parameter.side_effect = (
        mock_ssm_client.exceptions.ParameterNotFound
    )

    # Act
    cls.put_parameter(parameter_name, expected_value)

    # Assert
    assert cls.cache.exists(full_param_name)
    assert cls.cache.get(full_param_name) == expected_value


def test_put_parameter_skips_if_value_unchanged(cls, mock_ssm_client):
    # Arrange
    parameter_name = "test-param"
    existing_value = "test-value"

    # Setup mock to return existing value
    mock_ssm_client.get_parameter.return_value = {
        "Parameter": {
            "Value": existing_value,
        },
    }

    # Act
    cls.put_parameter(parameter_name, existing_value)

    # Assert
    assert not mock_ssm_client.put_parameter.called


def test_put_parameter_skips_if_value_cached_and_unchanged(cls, mock_ssm_client):
    # Arrange
    parameter_name = "test-param"
    existing_value = "test-value"
    full_param_name = f"/adf/{parameter_name}"

    # Setup mock to return existing value
    cls.cache.add(full_param_name, existing_value)

    # Act
    cls.put_parameter(parameter_name, existing_value)

    # Assert
    assert not mock_ssm_client.put_parameter.called


def test_delete_parameter_removes_from_cache(cls):
    # Arrange
    parameter_name = "test-param"
    full_param_name = f"/adf/{parameter_name}"
    cls.cache.add(full_param_name, "test-value")

    # Act
    cls.delete_parameter(parameter_name)

    # Assert
    assert not cls.cache.exists(full_param_name)


def test_delete_parameter_removes_from_cache_even_when_failing(cls, mock_ssm_client):
    # Arrange
    parameter_name = "test-param"
    full_param_name = f"/adf/{parameter_name}"
    cls.cache.add(full_param_name, "test-value")

    # Simulate parameter not found when deleting
    mock_ssm_client.delete_parameter.side_effect = (
        mock_ssm_client.exceptions.ParameterNotFound
    )

    # Act
    cls.delete_parameter(parameter_name)

    # Assert
    assert not cls.cache.exists(full_param_name)


def test_fetch_parameter_returns_cached_value(cls, mock_ssm_client):
    # Arrange
    parameter_name = "test-param"
    full_param_name = f"/adf/{parameter_name}"
    cached_value = "cached-value"
    cls.cache.add(full_param_name, cached_value)

    # Act
    result = cls.fetch_parameter(parameter_name)

    # Assert
    assert result == cached_value
    assert not mock_ssm_client.get_parameter.called


def test_fetch_parameter_caches_new_value(cls, mock_ssm_client):
    # Arrange
    parameter_name = "test-param"
    full_param_name = f"/adf/{parameter_name}"
    expected_value = "test-value"
    mock_ssm_client.get_parameter.return_value = {
        "Parameter": {
            "Value": expected_value,
        },
    }

    # Act
    result = cls.fetch_parameter(parameter_name)

    # Assert
    assert result == expected_value
    assert cls.cache.get(full_param_name) == expected_value


def test_fetch_parameter_caches_not_found_error(cls, mock_ssm_client):
    # Arrange
    parameter_name = "test-param"
    full_param_name = f"/adf/{parameter_name}"
    mock_ssm_client.get_parameter.side_effect = (
        mock_ssm_client.exceptions.ParameterNotFound
    )

    # Act & Assert
    with raises(ParameterNotFoundError):
        cls.fetch_parameter(parameter_name)

    # Verify the error is cached
    cached_value = cls.cache.get(full_param_name)
    assert isinstance(cached_value, ParameterNotFoundError)


def test_fetch_parameter_returns_cached_not_found_error(cls, mock_ssm_client):
    # Arrange
    parameter_name = "test-param"
    full_param_name = f"/adf/{parameter_name}"
    cached_error = ParameterNotFoundError("Parameter not found")
    cls.cache.add(full_param_name, cached_error)

    # Act & Assert
    with raises(ParameterNotFoundError):
        cls.fetch_parameter(parameter_name)
    assert not mock_ssm_client.get_parameter.called


def test_fetch_parameter_accept_not_found_with_cached_error(cls):
    # Arrange
    parameter_name = "test-param"
    full_param_name = f"/adf/{parameter_name}"
    default_value = "default"
    cached_error = ParameterNotFoundError("Parameter not found")
    cls.cache.add(full_param_name, cached_error)

    # Act
    result = cls.fetch_parameter_accept_not_found(
        parameter_name, default_value=default_value
    )

    # Assert
    assert result == default_value

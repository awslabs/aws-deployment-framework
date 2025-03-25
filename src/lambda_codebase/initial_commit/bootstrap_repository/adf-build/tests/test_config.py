# Copyright Amazon.com Inc. or its affiliates.
# SPDX-License-Identifier: MIT-0

# pylint: skip-file

import os
from errors import InvalidConfigError

from pytest import fixture, raises
from config import Config
from mock import Mock


@fixture
def cls():
    parameter_store = Mock()
    return Config(
        parameter_store=parameter_store,
        config_path="{0}/stubs/stub_adfconfig.yml".format(
            os.path.dirname(os.path.realpath(__file__))
        ),
    )


def test_validation(cls):
    assert (
        cls.config.get("main-notification-endpoint")[0].get("target")
        == "john@example.com"
    )
    assert cls.config.get("moves")[0].get("action") == "remove-base"


def test_validation_list_deployment_target(cls):
    cls.config_contents["regions"]["targets"] = "target1"
    cls._parse_config()
    assert cls.target_regions == ["target1"]


def test_validation_list_deployment_account_target(cls):
    cls.config_contents["regions"]["deployment-account"] = "target1"
    cls._parse_config()
    assert cls.deployment_account_region == "target1"


def test_raise_validation_remove_moves(cls):
    cls.config_contents.get("config").pop("moves", None)
    with raises(InvalidConfigError):
        assert cls._parse_config()


def test_raise_validation_remove_roles(cls):
    cls.config_contents.get("roles", None).pop("cross-account-access", None)
    with raises(InvalidConfigError):
        assert cls._parse_config()


def test_raise_validation_remove_deployment_target_region(cls):
    cls.config_contents.get("regions", None).pop("deployment-account", None)
    with raises(InvalidConfigError):
        assert cls._parse_config()


def test_raise_validation_length_deployment_target_region(cls):
    cls.config_contents["regions"]["deployment-account"] = [
        "region1",
        "region2",
    ]
    with raises(InvalidConfigError):
        assert cls._parse_config()

def test_raise_validation_deployment_maps_codebase_source_source_type(cls):
    cls.config_contents["config"]["deployment-maps"]["codebase-source"]["source-type"] = "github"
    with raises(InvalidConfigError):
        assert cls._parse_config()

def test_sorted_regions(cls):
    cls.config_contents["regions"]["deployment-account"] = [
        "us-east-1",
    ]
    cls.config_contents["regions"]["targets"] = [
        "us-west-2",
        "us-east-1",
        "eu-west-3",
    ]
    cls._parse_config()
    assert cls.sorted_regions() == [
        "us-east-1",
        "eu-west-3",
        "us-west-2",
    ]


def test_raise_validation_organizations_scp(cls):
    cls.config_contents["config"]["scp"]["keep-default-scp"] = "blah"
    with raises(InvalidConfigError):
        assert cls._parse_config()


def test_extensions_default_configuration(cls):
    cls._parse_config()
    assert cls.extensions == {"terraform": {"enabled": False}}


def test_extensions_default_configuration_with_custom(cls):
    cls.config_contents["extensions"] = {
        "another_extensions": {
            "enabled": True,
        },
    }
    cls._parse_config()
    assert cls.extensions == {
        "another_extensions": {"enabled": True},
        "terraform": {"enabled": False},
    }


def test_extensions_default_configuration_wont_override_custom(cls):
    cls.config_contents["extensions"] = {
        "another_extensions": {"enabled": True},
        "terraform": {"enabled": True},
    }
    cls._parse_config()
    assert cls.extensions == {
        "another_extensions": {"enabled": True},
        "terraform": {"enabled": True},
    }

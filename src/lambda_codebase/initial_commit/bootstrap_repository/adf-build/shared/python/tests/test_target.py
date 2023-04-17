# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

# pylint: skip-file

import os
import boto3
from errors import InvalidDeploymentMapError
from pytest import fixture, raises
from mock import Mock, patch
from .stubs import stub_target
from ..target import Target, TargetStructure


class MockTargetStructure:
    def __init__(self):
        self.account_list = []


class MockOrgClient:
    def __init__(self, return_value) -> None:
        self.values = return_value

    def dir_to_ou(self, path):
        return self.values


@fixture
def cls():
    cls = Target(
        path="/thing/path",
        target_structure=MockTargetStructure(),
        organizations=None,
        step={
            "regions": ["region1", "region2"],
        },
    )
    return cls


def test_account_is_active():
    assert Target._account_is_active({"Status": "ACTIVE"}) is True
    assert Target._account_is_active({"Status": "FAKE"}) is False


def test_fetch_accounts_for_target_ou_path():
    cls = Target(
        path="/thing/path",
        target_structure=MockTargetStructure(),
        organizations=None,
        step={
            "regions": ["region1", "region2"],
        },
    )

    with patch.object(cls, "_target_is_ou_path") as mock:
        cls.fetch_accounts_for_target()
        mock.assert_called_once_with()


def test_fetch_accounts_for_target_account_id():
    cls = Target(
        path="111111111111",
        target_structure=MockTargetStructure(),
        organizations=None,
        step={
            "regions": ["region1", "region2"],
        },
    )
    with patch.object(cls, "_target_is_account_id") as mock:
        cls.fetch_accounts_for_target()
        mock.assert_called_once_with()


def test_fetch_accounts_for_target_ou_id():
    cls = Target(
        path="ou-123fake",
        target_structure=MockTargetStructure(),
        organizations=None,
        step={
            "regions": ["region1", "region2"],
        },
    )
    with patch.object(cls, "_target_is_ou_id") as mock:
        cls.fetch_accounts_for_target()
        mock.assert_called_once_with()


def test_fetch_accounts_for_approval():
    cls = Target(
        path="approval",
        target_structure=MockTargetStructure(),
        organizations=None,
        step={
            "regions": ["region1", "region2"],
        },
    )
    with patch.object(cls, "_target_is_approval") as mock:
        cls.fetch_accounts_for_target()
        mock.assert_called_once_with()


def test_fetch_account_error():
    cls = Target(
        path="some_string",
        target_structure=MockTargetStructure(),
        organizations=Mock(),
        step={
            "regions": ["region1", "region2"],
        },
    )
    with raises(InvalidDeploymentMapError):
        cls.fetch_accounts_for_target()


def test_fetch_account_error_invalid_account_id():
    cls = Target(
        path="12345678901",  # 11 digits rather than 12 (invalid account id)
        target_structure=MockTargetStructure(),
        organizations=Mock(),
        step={
            "regions": ["region1", "region2"],
        },
    )
    with raises(InvalidDeploymentMapError):
        cls.fetch_accounts_for_target()


def test_target_structure_respects_wave():
    test_target_config = {"path": "/some/random/ou", "wave": {"size": 2}}
    target_structure = TargetStructure(
        target=test_target_config,
    )
    for step in target_structure.target:
        target = Target(
            path=test_target_config.get("path")[0],
            target_structure=target_structure,
            organizations=MockOrgClient(
                [
                    {"Name": "test-account-1", "Id": "1", "Status": "ACTIVE"},
                    {"Name": "test-account-2", "Id": "2", "Status": "ACTIVE"},
                    {"Name": "test-account-3", "Id": "3", "Status": "ACTIVE"},
                    {"Name": "test-account-4", "Id": "4", "Status": "ACTIVE"},
                    {"Name": "test-account-5", "Id": "5", "Status": "ACTIVE"},
                ]
            ),
            step={
                **step,
                "provider": "codedeploy",
                "regions": ["region1"],
            }
        )
        target.fetch_accounts_for_target()
        actions_per_target_account = target_structure.get_actions_per_target_account(target.regions,target.provider,target.properties.get("action"))
        waves = list(target.target_structure.generate_waves(actions_per_target_account=actions_per_target_account))
        assert len(waves) == 3

        assert len(waves[0]) == 2
        assert waves[0] == [
            {
                "id": "1",
                "name": "test-account-1",
                "path": "/some/random/ou",
                "properties": {},
                "provider": "codedeploy",
                "regions": ["region1"],
                "step_name": "",
            },
            {
                "id": "2",
                "name": "test-account-2",
                "path": "/some/random/ou",
                "properties": {},
                "provider": "codedeploy",
                "regions": ["region1"],
                "step_name": "",
            },
        ]

        assert len(waves[1]) == 2
        assert waves[1] == [
            {
                "id": "3",
                "name": "test-account-3",
                "path": "/some/random/ou",
                "properties": {},
                "provider": "codedeploy",
                "regions": ["region1"],
                "step_name": "",
            },
            {
                "id": "4",
                "name": "test-account-4",
                "path": "/some/random/ou",
                "properties": {},
                "provider": "codedeploy",
                "regions": ["region1"],
                "step_name": "",
            },
        ]

        assert len(waves[2]) == 1
        assert waves[2] == [
            {
                "id": "5",
                "name": "test-account-5",
                "path": "/some/random/ou",
                "properties": {},
                "provider": "codedeploy",
                "regions": ["region1"],
                "step_name": "",
            },
        ]

def test_target_structure_respects_multi_region():
    """ Validate behaviour with multiple accounts (x5) using Cloudformation default action (x2 actions) across several regions (x4)
    Limited to 20 actions per region should split by 3 waves"""
    test_target_config = {"path": "/some/random/ou", "wave": {"size": 20}}
    target_structure = TargetStructure(
        target=test_target_config,
    )
    for step in target_structure.target:
        target = Target(
            path=test_target_config.get("path")[0],
            target_structure=target_structure,
            organizations=MockOrgClient(
                [
                    {"Name": "test-account-1", "Id": "1", "Status": "ACTIVE"},
                    {"Name": "test-account-2", "Id": "2", "Status": "ACTIVE"},
                    {"Name": "test-account-3", "Id": "3", "Status": "ACTIVE"},
                    {"Name": "test-account-4", "Id": "4", "Status": "ACTIVE"},
                    {"Name": "test-account-5", "Id": "5", "Status": "ACTIVE"},
                ]
            ),
            step={
                **step,
                "provider": "cloudformation",
                "regions": ["region1", "region2", "region3", "region4"],
            }
        )
        target.fetch_accounts_for_target()
        actions_per_target_account = target_structure.get_actions_per_target_account(target.regions,target.provider,target.properties.get("action"))
        waves = list(target.target_structure.generate_waves(actions_per_target_account=actions_per_target_account))
        assert len(waves) == 3

        assert len(waves[0]) == 2 # x2 accounts x4 region x2 action = 16
        assert len(waves[1]) == 2 # x2 accounts x4 region x2 action = 16
        assert len(waves[2]) == 1 # x1 accounts x4 region x2 action = 8

def test_target_structure_respects_multi_action_single_region():
    """ Validate behaviour with multiple accounts (x30) using Cloudformation default actions (x2 actions) across single region (x1)
    Limited to 20 actions per region should split by 3 waves"""
    test_target_config = {"path": "/some/random/ou"}
    target_structure = TargetStructure(
        target=test_target_config,
    )
    for step in target_structure.target:
        target = Target(
            path=test_target_config.get("path")[0],
            target_structure=target_structure,

            organizations=MockOrgClient(
               [{"Name": f"test-account-{x}", "Id": x, "Status": "ACTIVE"} for x in range(30)]
            ),
            step={
                **step,
                "provider": "cloudformation",
                "regions": ["region1"],
            }
        )
        target.fetch_accounts_for_target()
        actions_per_target_account = target_structure.get_actions_per_target_account(target.regions,target.provider,target.properties.get("action"))
        waves = list(target.target_structure.generate_waves(actions_per_target_account=actions_per_target_account))
        assert len(waves) == 2

        assert len(waves[0]) == 25 # Asset x25 accounts x1 region x2 action = 50
        assert len(waves[1]) == 5 # Assert x5 account x1 region x2 action = 10


def test_target_wave_structure_respects_exclude_config():
    test_target_config = {
        "path": "/some/random/ou",
        "wave": {"size": 2},
        "exclude": ["5"],
    }
    target_structure = TargetStructure(
        target=test_target_config,
    )
    for step in target_structure.target:
        target = Target(
            path=test_target_config.get("path")[0],
            target_structure=target_structure,
            organizations=MockOrgClient(
                [
                    {"Name": "test-account-1", "Id": "1", "Status": "ACTIVE"},
                    {"Name": "test-account-2", "Id": "2", "Status": "ACTIVE"},
                    {"Name": "test-account-3", "Id": "3", "Status": "ACTIVE"},
                    {"Name": "test-account-4", "Id": "4", "Status": "ACTIVE"},
                    {"Name": "test-account-5", "Id": "5", "Status": "ACTIVE"},
                    {"Name": "test-account-6", "Id": "6", "Status": "ACTIVE"},
                ]
            ),
            step={
                **step,
                "regions": "region1",
                "properties":{"action":"REPLACE_ON_FAILURE"}
            }
        )
        target.fetch_accounts_for_target()
        actions_per_target_account = target_structure.get_actions_per_target_account(target.regions,target.provider,target.properties.get("action"))
        waves = list(target.target_structure.generate_waves(actions_per_target_account=actions_per_target_account))
        assert len(waves) == 3

        assert len(waves[0]) == 2
        assert waves[0] == [
            {
                "id": "1",
                "name": "test-account-1",
                "path": "/some/random/ou",
                "properties":{"action":"REPLACE_ON_FAILURE"},
                "provider": "cloudformation",
                "regions": ["region1"],
                "step_name": "",
            },
            {
                "id": "2",
                "name": "test-account-2",
                "path": "/some/random/ou",
                "properties":{"action":"REPLACE_ON_FAILURE"},
                "provider": "cloudformation",
                "regions": ["region1"],
                "step_name": "",
            },
        ]

        assert len(waves[1]) == 2
        assert waves[1] == [
            {
                "id": "3",
                "name": "test-account-3",
                "path": "/some/random/ou",
                "properties":{"action":"REPLACE_ON_FAILURE"},
                "provider": "cloudformation",
                "regions": ["region1"],
                "step_name": "",
            },
            {
                "id": "4",
                "name": "test-account-4",
                "path": "/some/random/ou",
                "properties":{"action":"REPLACE_ON_FAILURE"},
                "provider": "cloudformation",
                "regions": ["region1"],
                "step_name": "",
            },
        ]

        assert len(waves[2]) == 1
        assert waves[2] == [
            {
                "id": "6",
                "name": "test-account-6",
                "path": "/some/random/ou",
                "properties":{"action":"REPLACE_ON_FAILURE"},
                "provider": "cloudformation",
                "regions": ["region1"],
                "step_name": "",
            },
        ]

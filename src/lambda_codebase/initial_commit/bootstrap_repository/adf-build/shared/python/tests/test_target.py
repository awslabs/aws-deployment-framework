# Copyright Amazon.com Inc. or its affiliates.
# SPDX-License-Identifier: MIT-0

# pylint: skip-file

import os
import boto3
from errors import InvalidDeploymentMapError
from pytest import fixture, raises
from mock import Mock, patch,call
from .stubs import stub_target
from ..target import Target, TargetStructure
from ..target import TooManyActionsError
from parameter_store import ParameterStore


class MockTargetStructure:
    def __init__(self):
        self.account_list = []


class MockOrgClient:
    def __init__(self, return_value) -> None:
        self.values = return_value

    def get_accounts_in_path(
        self, path, ou_id, resolve_children=False, excluded_paths=[]
    ):
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
    parameter_store = Mock()
    parameter_store.client.put_parameter.return_value = True
    with patch.object(ParameterStore, 'fetch_parameter') as mock:
        expected_calls = [
            call(
                'deployment_maps/allow_empty_target',
                'disabled',
            ),
        ]
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
            mock.assert_called_once_with(resolve_children=False)


def test_fetch_accounts_for_target_account_id():
    parameter_store = Mock()
    parameter_store.client.put_parameter.return_value = True
    with patch.object(ParameterStore, 'fetch_parameter') as mock:
        expected_calls = [
            call(
                'deployment_maps/allow_empty_target',
                'disabled',
            ),
        ]
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
    parameter_store = Mock()
    parameter_store.client.put_parameter.return_value = True
    with patch.object(ParameterStore, 'fetch_parameter') as mock:
        expected_calls = [
            call(
                'deployment_maps/allow_empty_target',
                'disabled',
            ),
        ]
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
    parameter_store = Mock()
    parameter_store.client.put_parameter.return_value = True
    with patch.object(ParameterStore, 'fetch_parameter') as mock:
        expected_calls = [
            call(
                'deployment_maps/allow_empty_target',
                'disabled',
            ),
        ]
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
    parameter_store = Mock()
    parameter_store.client.put_parameter.return_value = True
    with patch.object(ParameterStore, 'fetch_parameter') as mock:
        expected_calls = [
            call(
                'deployment_maps/allow_empty_target',
                'disabled',
            ),
        ]
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
    parameter_store = Mock()
    parameter_store.client.put_parameter.return_value = True
    with patch.object(ParameterStore, 'fetch_parameter') as mock:
        expected_calls = [
            call(
                'deployment_maps/allow_empty_target',
                'disabled',
            ),
        ]
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
    parameter_store = Mock()
    parameter_store.client.put_parameter.return_value = True
    with patch.object(ParameterStore, 'fetch_parameter') as mock:
        expected_calls = [
            call(
                'deployment_maps/allow_empty_target',
                'disabled',
            ),
        ]
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
            waves, total_actions = target.target_structure.generate_waves(target=target)
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

def test_target_structure_too_many_actions():
    """Validates that when too many targets are defined then total_actions would
    an exception. """
    parameter_store = Mock()
    parameter_store.client.put_parameter.return_value = True
    with patch.object(ParameterStore, 'fetch_parameter') as mock:
        expected_calls = [
            call(
                'deployment_maps/allow_empty_target',
                'disabled',
            ),
        ]
        test_target_config = {"path": "/some/random/ou",}
        target_structure = TargetStructure(
            target=test_target_config,
        )
        for step in target_structure.target:
            target = Target(
                path=test_target_config.get("path")[0],
                target_structure=target_structure,

                organizations=MockOrgClient([
                    {"Name": f"test-account-{x}", "Id": x, "Status": "ACTIVE"}
                    for x in range(200)
                ]),
                step={
                    **step,
                    "provider": "cloudformation",
                    "regions": ["region1", "region2", "region3", "region4"]
                }
            )
            target.fetch_accounts_for_target()
            waves, total_actions = target.target_structure.generate_waves(
                target=target
            )
            with raises(TooManyActionsError):
                target.target_structure.validate_actions_limit(
                    "dummy_name",
                    total_actions
                )


def test_target_structure_respects_multi_region():
    """ Validate behavior with multiple accounts (x5) using cloudformation
    default action (x2 actions) across several regions (x4)
    Limited to 20 actions per region should split by 3 waves"""
    parameter_store = Mock()
    parameter_store.client.put_parameter.return_value = True
    with patch.object(ParameterStore, 'fetch_parameter') as mock:
        expected_calls = [
            call(
                'deployment_maps/allow_empty_target',
                'disabled',
            ),
        ]
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

            waves, total_actions = target.target_structure.generate_waves(target=target)

            assert len(waves) == 3
            assert total_actions == 40 # assert accounts(5) * regions(4) * actions(2) = 40
            assert len(waves[0]) == 2 # assert accounts(2) * regions(4) * actions(2) = 16
            assert len(waves[1]) == 2 # assert accounts(2) * regions(4) * actions(2) = 16
            assert len(waves[2]) == 1 # assert accounts(1) * regions(4) * actions(2) = 8


def test_target_structure_respects_multi_action_single_region():
    """ Validate behavior with multiple accounts (x30) using cloudformation
    default actions (x2 actions) across single region (x1)
    Limited to 20 actions per region should split by 2 waves"""
    parameter_store = Mock()
    parameter_store.client.put_parameter.return_value = True
    with patch.object(ParameterStore, 'fetch_parameter') as mock:
        expected_calls = [
            call(
                'deployment_maps/allow_empty_target',
                'disabled',
            ),
        ]
        test_target_config = {"path": "/some/random/ou", "wave": {"size": 20}}
        target_structure = TargetStructure(
            target=test_target_config,
        )
        for step in target_structure.target:
            target = Target(
                path=test_target_config.get("path")[0],
                target_structure=target_structure,

                organizations=MockOrgClient([
                    {"Name": f"test-account-{x}", "Id": x, "Status": "ACTIVE"}
                    for x in range(30)
                ]),
                step={
                    **step,
                    "provider": "cloudformation",
                    "regions": ["region1"],
                }
            )
            target.fetch_accounts_for_target()
            waves, total_actions = target.target_structure.generate_waves(
                target=target
            )

            assert len(waves) == 3
            assert total_actions == 60 # assert accounts(30) * regions(1) * actions(2) = 60
            assert len(waves[0]) == 10 # assert accounts(20) * region(1) * action(2) = 20
            assert len(waves[1]) == 10 # assert accounts(10) * region(1) * action(2) = 20
            assert len(waves[2]) == 10 # assert accounts(10) * region(1) * action(2) = 20


def test_target_structure_respects_multi_action_multi_region():
    """ Validate behavior with multiple accounts (x34) using cloudformation
    default actions (x2 actions) across two region (x2)
    Limited to default 100 actions per region should split by 2 waves"""
    parameter_store = Mock()
    parameter_store.client.put_parameter.return_value = True
    with patch.object(ParameterStore, 'fetch_parameter') as mock:
        expected_calls = [
            call(
                'deployment_maps/allow_empty_target',
                'disabled',
            ),
        ]
        test_target_config = {"path": "/some/random/ou"}
        target_structure = TargetStructure(
            target=test_target_config,
        )
        for step in target_structure.target:
            target = Target(
                path=test_target_config.get("path")[0],
                target_structure=target_structure,

                organizations=MockOrgClient(
                    [
                        {"Name": f"test-account-{x}", "Id": x, "Status": "ACTIVE"}
                        for x in range(34)
                    ]
                ),
                step={
                    **step,
                    "provider": "cloudformation",
                    "regions": ["us-east-1", "eu-central-1"],
                }
            )
            target.fetch_accounts_for_target()

            waves, total_actions = target.target_structure.generate_waves(target=target)
            assert len(waves) == 2
            assert total_actions == 136 # assert accounts(34) * regions(2) * actions(2) = 136
            assert len(waves[0]) == 25 # assert accounts(25) * regions(2) * actions(2) = 100
            assert len(waves[1]) == 9 # assert accounts(9) * regions(2) * actions(2) = 36



def test_target_structure_respects_change_set_approval_single_region():
    """ Validate behavior with multiple accounts (x60) using cloudformation
    change_set_approval (x3 actions) across single region (x1)
    Limited to default 100 actions per region"""
    parameter_store = Mock()
    parameter_store.client.put_parameter.return_value = True
    with patch.object(ParameterStore, 'fetch_parameter') as mock:
        expected_calls = [
            call(
                'deployment_maps/allow_empty_target',
                'disabled',
            ),
        ]
        test_target_config = {"path": "/some/random/ou"}
        target_structure = TargetStructure(
            target=test_target_config,
        )
        for step in target_structure.target:
            target = Target(
                path=test_target_config.get("path")[0],
                target_structure=target_structure,

                organizations=MockOrgClient(
                    [
                        {"Name": f"test-account-{x}", "Id": x, "Status": "ACTIVE"}
                        for x in range(60)
                    ]
                ),
                step={
                    **step,
                    "provider": "cloudformation",
                    "properties": {
                        "change_set_approval": True,
                    },
                    "regions": ["us-east-1"],
                }
            )
            target.fetch_accounts_for_target()

            waves, total_actions = target.target_structure.generate_waves(target=target)
            assert len(waves) == 2
            assert total_actions == 180 # assert accounts(60) * regions(1) * actions(3) = 180
            assert len(waves[0]) == 33 # assert accounts(33) * regions(1) * actions(3) = 99
            assert len(waves[1]) == 27 # assert accounts(27) * regions(1) * actions(3) = 81


def test_target_wave_structure_respects_exclude_config():
    parameter_store = Mock()
    parameter_store.client.put_parameter.return_value = True
    with patch.object(ParameterStore, 'fetch_parameter') as mock:
        expected_calls = [
            call(
                'deployment_maps/allow_empty_target',
                'disabled',
            ),
        ]
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
                    "properties": {
                        "action": "REPLACE_ON_FAILURE",
                    },
                }
            )
            target.fetch_accounts_for_target()
            waves, _ = target.target_structure.generate_waves(target=target)
            assert len(waves) == 3

            assert len(waves[0]) == 2
            assert waves[0] == [
                {
                    "id": "1",
                    "name": "test-account-1",
                    "path": "/some/random/ou",
                    "properties": {
                        "action": "REPLACE_ON_FAILURE",
                    },
                    "provider": "cloudformation",
                    "regions": ["region1"],
                    "step_name": "",
                },
                {
                    "id": "2",
                    "name": "test-account-2",
                    "path": "/some/random/ou",
                    "properties": {
                        "action": "REPLACE_ON_FAILURE",
                    },
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
                    "properties": {
                        "action": "REPLACE_ON_FAILURE",
                    },
                    "provider": "cloudformation",
                    "regions": ["region1"],
                    "step_name": "",
                },
                {
                    "id": "4",
                    "name": "test-account-4",
                    "path": "/some/random/ou",
                    "properties": {
                        "action": "REPLACE_ON_FAILURE",
                    },
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
                    "properties": {
                        "action": "REPLACE_ON_FAILURE",
                    },
                    "provider": "cloudformation",
                    "regions": ["region1"],
                    "step_name": "",
                },
            ]

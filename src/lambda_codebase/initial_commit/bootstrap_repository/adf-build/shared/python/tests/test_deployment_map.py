# Copyright Amazon.com Inc. or its affiliates.
# SPDX-License-Identifier: MIT-0

# pylint: skip-file

import os

from pytest import fixture
from mock import Mock
from ..pipeline import Pipeline
from ..deployment_map import DeploymentMap


@fixture
def cls():
    return DeploymentMap(
        parameter_store=None,
        s3=None,
        pipeline_name_prefix="adf",
        map_path="{0}/stubs/stub_deployment_map.yml".format(
            os.path.dirname(os.path.realpath(__file__))
        ),
    )


def test_update_deployment_parameters(cls):
    cls.s3 = Mock()
    cls.s3.put_object.return_value = None

    pipeline = Pipeline(
        {
            "name": "pipeline",
            "params": {"key": "value"},
            "targets": [],
            "default_providers": {
                "source": {
                    "name": "codecommit",
                    "properties": {
                        "account_id": 111111111111,
                    },
                }
            },
        }
    )

    # Targets : [[account_id, account_id], [account_id, account_id]]
    pipeline.template_dictionary = {
        "targets": [
            # Array holding all waves
            [
                # First wave of targets
                [
                    # First batch within the first wave
                    {
                        "id": "111111111111",
                        "name": "some_account",
                        "path": "/fake/path",
                        "properties": {},
                        "provider": {},
                        "regions": ["eu-west-1"],
                        "step_name": "",
                    },
                ]
            ]
        ]
    }

    cls.update_deployment_parameters(pipeline)
    assert cls.account_ou_names["some_account"] == "/fake/path"


def test_update_deployment_parameters_waves(cls):
    cls.s3 = Mock()
    cls.s3.put_object.return_value = None

    pipeline = Pipeline({
        "name": "pipeline",
        "params": {"key": "value"},
        "targets": [],
        "default_providers": {
            "source": {
                "name": "codecommit",
                "properties": {
                    "account_id": 111111111111,
                }
            }
        }
    })
    pipeline.template_dictionary = {
        "targets": [  # Array holding all waves
            [  # First wave of targets
                [  # First batch within the first wave
                    {  # First target in first wave
                        "name": "first",
                        "path": "/first/path",
                    },
                    {  # Second target in first wave
                        "name": "second",
                        "path": "/second/path",
                    }
                ],
                [  # Second batch within the first wave
                    {
                        # Third target in first wave
                        "name": "third",
                        "path": "/third/path",
                    },
                ],
            ],
            [  # Second wave of targets
                [  # First batch within the second wave
                    {
                        # Third target in first wave
                        "name": "approval",
                    },
                ],
            ],
            [  # Third wave of targets
                [  # First batch within the third wave
                    {
                        # Third target in first wave
                        "name": "fourth",
                        "path": "/fourth/path",
                    },
                ],
            ]
        ],
    }

    cls.update_deployment_parameters(pipeline)
    for target in ['first', 'second', 'third', 'fourth']:
        assert cls.account_ou_names[target] == f'/{target}/path'

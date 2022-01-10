# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

# pylint: skip-file

import os
import boto3

from errors import InvalidDeploymentMapError
from pytest import fixture, raises
from mock import Mock
from ..pipeline import Pipeline
from ..deployment_map import DeploymentMap


@fixture
def cls():
    return DeploymentMap(
        parameter_store=None,
        s3=None,
        pipeline_name_prefix='adf',
        map_path='{0}/stubs/stub_deployment_map.yml'.format(
            os.path.dirname(os.path.realpath(__file__))
        )
    )

def test_update_deployment_parameters(cls):
    cls.s3 = Mock()
    cls.s3.put_object.return_value = None

    pipeline = Pipeline({
        "name": "pipeline",
        "params": {"key": "value"},
        "targets": [],
        "default_providers": {
            "source": {
                "name": "codecommit",
                "properties" : {
                    "account_id": 111111111111,
                }
            }
        }
    })
    pipeline.template_dictionary = {
        "targets": [[{"name": "some_pipeline", "path": "/fake/path"}]]
    }

    cls.update_deployment_parameters(pipeline)
    assert cls.account_ou_names['some_pipeline'] == '/fake/path'

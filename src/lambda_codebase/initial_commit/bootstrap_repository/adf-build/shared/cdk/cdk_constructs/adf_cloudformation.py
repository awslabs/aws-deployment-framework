# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""Construct related to CloudFormation Input
"""

import os
from aws_cdk import (
    core
)

from cdk_constructs import adf_codepipeline

ADF_DEPLOYMENT_REGION = os.environ["AWS_REGION"]
ADF_DEFAULT_BUILD_TIMEOUT = 20


class CloudFormation(core.Construct):
    def __init__(self, scope: core.Construct, id: str, **kwargs): #pylint: disable=W0622, W0235
        super().__init__(scope, id, **kwargs)

    @staticmethod
    def generate_actions(targets, region, map_params, target_approval_mode):
        _actions = []
        if not isinstance(targets, list):
            targets = [targets]
        for target in targets:
            _actions.append(
                adf_codepipeline.Action(
                    name="{0}-{1}-create".format(target['name'], region),
                    provider="CloudFormation",
                    category="Deploy",
                    region=region,
                    target=target,
                    run_order=1,
                    action_mode="CHANGE_SET_REPLACE",
                    map_params=map_params,
                    action_name="{0}-{1}-create".format(target['name'], region)
                ).config,
            )
            if target_approval_mode:
                _actions.append(
                    adf_codepipeline.Action(
                        name="{0}-{1}".format(target['name'], region),
                        provider="Manual",
                        category="Approval",
                        region=region,
                        target=target,
                        run_order=2,
                        map_params=map_params,
                        action_name="{0}-{1}".format(target['name'], region)
                    ).config
                )
            _actions.append(
                adf_codepipeline.Action(
                    name="{0}-{1}-execute".format(target['name'], region),
                    provider="CloudFormation",
                    category="Deploy",
                    region=region,
                    target=target,
                    run_order=3 if target.get('properties', {}).get('change_set_approval') else 2,
                    action_mode="CHANGE_SET_EXECUTE",
                    map_params=map_params,
                    action_name="{0}-{1}-execute".format(target['name'], region)
                ).config
            )
        return _actions

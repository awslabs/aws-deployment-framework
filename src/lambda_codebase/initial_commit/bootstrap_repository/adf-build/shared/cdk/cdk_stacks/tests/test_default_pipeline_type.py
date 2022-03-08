# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

# pylint: skip-file

from aws_cdk import core
from cdk_stacks.main import PipelineStack


def test_pipeline_creation_outputs_as_expected_when_input_has_1_target_with_2_waves():
    region_name = "eu-central-1"
    account_id = "123456789012"

    stack_input = {
        "input": {
            "params": {},
            "default_providers": {"deploy": {"provider": "codedeploy"}},
            "regions": {},
        },
        "ssm_params": {"fake-region": {}},
    }

    stack_input["input"]["name"] = "test-stack"
    stack_input["input"]["environments"] = {
        "targets": [
            [
                [
                    {"name": "account-1", "id": "001", "regions": ["eu-west-1"]},
                    {"name": "account-2", "id": "002", "regions": ["eu-west-1"]},
                    {"name": "account-3", "id": "003", "regions": ["eu-west-1"]},
                ],
                [
                    {"name": "account-4", "id": "004", "regions": ["eu-west-1"]},
                    {"name": "account-5", "id": "005", "regions": ["eu-west-1"]},
                    {"name": "account-6", "id": "006", "regions": ["eu-west-1"]},
                ],
            ],
        ]
    }

    stack_input["input"]["default_providers"]["source"] = {
        "provider": "codecommit",
        "properties": {"account_id": "123456789012"},
    }
    stack_input["input"]["default_providers"]["build"] = {
        "provider": "codebuild",
        "properties": {"account_id": "123456789012"},
    }

    stack_input["ssm_params"][region_name] = {
        "modules": "fake-bucket-name",
        "kms": f"arn:aws:kms:{region_name}:{account_id}:key/my-unique-kms-key-id",
    }
    app = core.App()
    PipelineStack(app, stack_input)

    cloud_assembly = app.synth()
    resources = {
        k[0:-8]: v for k, v in cloud_assembly.stacks[0].template["Resources"].items()
    }
    code_pipeline = resources["codepipeline"]
    assert code_pipeline["Type"] == "AWS::CodePipeline::Pipeline"
    assert len(code_pipeline["Properties"]["Stages"]) == 4

    target_1_wave_1 = code_pipeline["Properties"]["Stages"][2]
    assert target_1_wave_1["Name"] == "deployment-stage-1-wave-0"
    assert len(target_1_wave_1["Actions"]) == 3

    target_1_wave_2 = code_pipeline["Properties"]["Stages"][3]
    assert target_1_wave_2["Name"] == "deployment-stage-1-wave-1"
    assert len(target_1_wave_2["Actions"]) == 3


def test_pipeline_creation_outputs_as_expected_when_input_has_2_targets_with_2_waves_and_1_wave():
    region_name = "eu-central-1"
    account_id = "123456789012"

    stack_input = {
        "input": {
            "params": {},
            "default_providers": {"deploy": {"provider": "codedeploy"}},
            "regions": {},
        },
        "ssm_params": {"fake-region": {}},
    }

    stack_input["input"]["name"] = "test-stack"
    stack_input["input"]["environments"] = {
        "targets": [
            [
                [
                    {"name": "account-1", "id": "001", "regions": ["eu-west-1"]},
                    {"name": "account-2", "id": "002", "regions": ["eu-west-1"]},
                    {"name": "account-3", "id": "003", "regions": ["eu-west-1"]},
                ],
                [
                    {"name": "account-4", "id": "004", "regions": ["eu-west-1"]},
                    {"name": "account-5", "id": "005", "regions": ["eu-west-1"]},
                    {"name": "account-6", "id": "006", "regions": ["eu-west-1"]},
                ],
            ],
            [[{"name": "account-7", "id": "007", "regions": ["eu-west-2"]}]],
        ]
    }

    stack_input["input"]["default_providers"]["source"] = {
        "provider": "codecommit",
        "properties": {"account_id": "123456789012"},
    }
    stack_input["input"]["default_providers"]["build"] = {
        "provider": "codebuild",
        "properties": {"account_id": "123456789012"},
    }

    stack_input["ssm_params"][region_name] = {
        "modules": "fake-bucket-name",
        "kms": f"arn:aws:kms:{region_name}:{account_id}:key/my-unique-kms-key-id",
    }
    app = core.App()
    PipelineStack(app, stack_input)

    cloud_assembly = app.synth()
    resources = {
        k[0:-8]: v for k, v in cloud_assembly.stacks[0].template["Resources"].items()
    }
    code_pipeline = resources["codepipeline"]
    assert code_pipeline["Type"] == "AWS::CodePipeline::Pipeline"
    assert len(code_pipeline["Properties"]["Stages"]) == 5

    target_1_wave_1 = code_pipeline["Properties"]["Stages"][2]
    assert target_1_wave_1["Name"] == "deployment-stage-1-wave-0"
    assert len(target_1_wave_1["Actions"]) == 3

    target_1_wave_2 = code_pipeline["Properties"]["Stages"][3]
    assert target_1_wave_2["Name"] == "deployment-stage-1-wave-1"
    assert len(target_1_wave_2["Actions"]) == 3

    target_2_wave_1 = code_pipeline["Properties"]["Stages"][4]
    assert target_2_wave_1["Name"] == "deployment-stage-2-wave-0"
    assert len(target_2_wave_1["Actions"]) == 1    

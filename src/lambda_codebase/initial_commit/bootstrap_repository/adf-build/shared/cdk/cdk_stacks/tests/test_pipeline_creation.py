# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

# pylint: skip-file

import pytest
import os

from mock import patch
from aws_cdk import core
from cdk_stacks.main import PipelineStack


@patch("cdk_stacks.main.generate_default_pipeline")
def test_pipeline_generation_fails_if_pipeline_type_is_not_specified(mock):
    stack_input = {"input": {"params": {}}}
    stack_input["input"]["name"] = "test-stack"
    stack_input["input"]["params"]["type"] = "fail"
    app = core.App()
    with pytest.raises(ValueError):
        pipeline_stack = PipelineStack(app, stack_input)
    mock.assert_not_called()


@patch("cdk_stacks.main.generate_default_pipeline")
def test_pipeline_generation_works_when_no_type_specified(mock):
    stack_input = {"input": {"params": {}}}
    stack_input["input"]["name"] = "test-stack"
    app = core.App()
    PipelineStack(app, stack_input)
    mock.assert_called()


@patch("cdk_stacks.main.generate_default_pipeline")
def test_pipeline_generation_works_when_no_type_specified(mock):
    stack_input = {"input": {"params": {}}}
    stack_input["input"]["name"] = "test-stack"
    stack_input["input"]["params"]["type"] = "Default"

    app = core.App()
    PipelineStack(app, stack_input)
    mock.assert_called()


def test_pipeline_creation_outputs_as_expected_when_source_is_s3_and_build_is_codebuild():
    region_name = "eu-central-1"
    account_id = "123456789012"

    stack_input = {
        "input": {"params": {}, "default_providers": {}, "regions": {}},
        "ssm_params": {"fake-region": {}},
    }

    stack_input["input"]["name"] = "test-stack"

    stack_input["input"]["default_providers"]["source"] = {
        "provider": "s3",
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
    resources = {k[0:-8]: v for k, v in cloud_assembly.stacks[0].template['Resources'].items()}
    code_pipeline = resources['codepipeline']
    assert code_pipeline['Type'] == "AWS::CodePipeline::Pipeline"
    assert len(code_pipeline["Properties"]["Stages"]) == 2

    source_stage = code_pipeline['Properties']["Stages"][0]
    assert len(source_stage['Actions']) == 1

    source_stage_action = source_stage['Actions'][0]
    assert source_stage_action['ActionTypeId']['Category'] == "Source"
    assert source_stage_action['ActionTypeId']['Owner'] == "AWS"
    assert source_stage_action['ActionTypeId']['Provider'] == "S3"

    build_stage = code_pipeline['Properties']["Stages"][1]
    build_stage_action = build_stage['Actions'][0]
    assert build_stage_action['ActionTypeId']['Category'] == "Build"
    assert build_stage_action['ActionTypeId']['Owner'] == "AWS"
    assert build_stage_action['ActionTypeId']['Provider'] == "CodeBuild"

    assert len(build_stage['Actions']) == 1


def test_pipeline_creation_outputs_as_expected_when_source_is_codecommit_and_build_is_codebuild():
    region_name = "eu-central-1"
    acount_id = "123456789012"

    stack_input = {
        "input": {"params": {}, "default_providers": {}, "regions": {}},
        "ssm_params": {"fake-region": {}},
    }

    stack_input["input"]["name"] = "test-stack"

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
        "kms": f"arn:aws:kms:{region_name}:{acount_id}:key/my-unique-kms-key-id",
    }
    app = core.App()
    PipelineStack(app, stack_input)

    cloud_assembly = app.synth()
    resources = {k[0:-8]: v for k, v in cloud_assembly.stacks[0].template['Resources'].items()}
    code_pipeline = resources['codepipeline']
    assert code_pipeline['Type'] == "AWS::CodePipeline::Pipeline"
    assert len(code_pipeline["Properties"]["Stages"]) == 2

    source_stage = code_pipeline['Properties']["Stages"][0]
    assert len(source_stage['Actions']) == 1

    source_stage_action = source_stage['Actions'][0]
    assert source_stage_action['ActionTypeId']['Category'] == "Source"
    assert source_stage_action['ActionTypeId']['Owner'] == "AWS"
    assert source_stage_action['ActionTypeId']['Provider'] == "CodeCommit"

    build_stage = code_pipeline['Properties']["Stages"][1]
    build_stage_action = build_stage['Actions'][0]
    assert build_stage_action['ActionTypeId']['Category'] == "Build"
    assert build_stage_action['ActionTypeId']['Owner'] == "AWS"
    assert build_stage_action['ActionTypeId']['Provider'] == "CodeBuild"

    assert "OutputArtifactFormat" not in source_stage_action['Configuration']

    assert len(build_stage['Actions']) == 1


def test_pipeline_creation_outputs_as_expected_when_source_is_codecommit_with_codebuild_clone_ref_and_build_is_codebuild():
    region_name = "eu-central-1"
    acount_id = "123456789012"

    stack_input = {
        "input": {"params": {}, "default_providers": {}, "regions": {}},
        "ssm_params": {"fake-region": {}},
    }

    stack_input["input"]["name"] = "test-stack"

    stack_input["input"]["default_providers"]["source"] = {
        "provider": "codecommit",
        "properties": {"account_id": "123456789012", "output_artifact_format": "CODEBUILD_CLONE_REF"},
    }
    stack_input["input"]["default_providers"]["build"] = {
        "provider": "codebuild",
        "properties": {"account_id": "123456789012"},
    }

    stack_input["ssm_params"][region_name] = {
        "modules": "fake-bucket-name",
        "kms": f"arn:aws:kms:{region_name}:{acount_id}:key/my-unique-kms-key-id",
    }
    app = core.App()
    PipelineStack(app, stack_input)

    cloud_assembly = app.synth()
    resources = {k[0:-8]: v for k, v in cloud_assembly.stacks[0].template['Resources'].items()}
    code_pipeline = resources['codepipeline']
    assert code_pipeline['Type'] == "AWS::CodePipeline::Pipeline"
    assert len(code_pipeline["Properties"]["Stages"]) == 2

    source_stage = code_pipeline['Properties']["Stages"][0]
    assert len(source_stage['Actions']) == 1

    source_stage_action = source_stage['Actions'][0]
    assert source_stage_action['ActionTypeId']['Category'] == "Source"
    assert source_stage_action['ActionTypeId']['Owner'] == "AWS"
    assert source_stage_action['ActionTypeId']['Provider'] == "CodeCommit"
    assert source_stage_action['Configuration']['OutputArtifactFormat'] == "CODEBUILD_CLONE_REF"

    build_stage = code_pipeline['Properties']["Stages"][1]
    build_stage_action = build_stage['Actions'][0]
    assert build_stage_action['ActionTypeId']['Category'] == "Build"
    assert build_stage_action['ActionTypeId']['Owner'] == "AWS"
    assert build_stage_action['ActionTypeId']['Provider'] == "CodeBuild"

    assert len(build_stage['Actions']) == 1


def test_pipeline_creation_outputs_with_codeartifact_trigger():
    region_name = "eu-central-1"
    acount_id = "123456789012"

    stack_input = {
        "input": {"params": {}, "default_providers": {}, "regions": {}, "triggers": {"triggered_by": {"code_artifact": {"repository": "my_test_repo"} }}},
        "ssm_params": {"fake-region": {}},
    }

    stack_input["input"]["name"] = "test-stack"

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
        "kms": f"arn:aws:kms:{region_name}:{acount_id}:key/my-unique-kms-key-id",
    }
    app = core.App()
    PipelineStack(app, stack_input)

    cloud_assembly = app.synth()
    resources = {k[0:-8]: v for k, v in cloud_assembly.stacks[0].template['Resources'].items()}
    trigger = resources['codepipelinecodeartifactpipelinetriggermytestrepoall']
    assert trigger["Type"] == "AWS::Events::Rule"
    assert trigger["Properties"]["EventPattern"]["detail-type"] == ["CodeArtifact Package Version State Change"]
    assert trigger["Properties"]["EventPattern"]["source"] == ["aws.codeartifact"]
    assert trigger["Properties"]["EventPattern"]["detail"] == {"repositoryName": "my_test_repo"}


def test_pipeline_creation_outputs_with_codeartifact_trigger_with_package_name():
    region_name = "eu-central-1"
    acount_id = "123456789012"

    stack_input = {
        "input": {"params": {}, "default_providers": {}, "regions": {}, "triggers": {"triggered_by": {"code_artifact": {"repository": "my_test_repo", "package": "my_test_package"} }}},
        "ssm_params": {"fake-region": {}},
    }

    stack_input["input"]["name"] = "test-stack"

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
        "kms": f"arn:aws:kms:{region_name}:{acount_id}:key/my-unique-kms-key-id",
    }
    app = core.App()
    PipelineStack(app, stack_input)

    cloud_assembly = app.synth()
    resources = {k[0:-8]: v for k, v in cloud_assembly.stacks[0].template['Resources'].items()}
    trigger = resources['codepipelinecodeartifactpipelinetriggermytestrepomytestpackage']
    assert trigger["Type"] == "AWS::Events::Rule"
    assert trigger["Properties"]["EventPattern"]["detail-type"] == ["CodeArtifact Package Version State Change"]
    assert trigger["Properties"]["EventPattern"]["source"] == ["aws.codeartifact"]
    assert trigger["Properties"]["EventPattern"]["detail"] == {"repositoryName": "my_test_repo", "packageName": "my_test_package"}


def test_pipeline_creation_outputs_with_invalid_trigger_type():
    region_name = "eu-central-1"
    acount_id = "123456789012"

    stack_input = {
        "input": {"params": {}, "default_providers": {}, "regions": {}, "triggers": {"triggered_by": {"infinidash": {"arn": "arn:aws:11111111:us-east-1:infinidash/dash:blahblahblah"} }}},
        "ssm_params": {"fake-region": {}},
    }

    stack_input["input"]["name"] = "test-stack"

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
        "kms": f"arn:aws:kms:{region_name}:{acount_id}:key/my-unique-kms-key-id",
    }
    app = core.App()


    with pytest.raises(Exception) as e_info:
        PipelineStack(app, stack_input)
        cloud_assembly = app.synth()

    error_message = str(e_info.value)
    assert error_message.find("is not currently supported as a pipeline trigger") >= 0


def test_pipeline_creation_outputs_as_expected_when_notification_endpoint_is_chatbot():
    region_name = "eu-central-1"
    acount_id = "123456789012"

    stack_input = {
        "input": {"params": {"notification_endpoint": {"target": "fake-config", "type": "chat_bot"}}, "default_providers": {}, "regions": {}, },
        "ssm_params": {"fake-region": {}},
    }

    stack_input["input"]["name"] = "test-stack"

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
        "kms": f"arn:aws:kms:{region_name}:{acount_id}:key/my-unique-kms-key-id",
    }
    app = core.App()
    PipelineStack(app, stack_input)

    cloud_assembly = app.synth()
    resources = {k[0:-8]: v for k, v in cloud_assembly.stacks[0].template['Resources'].items()}
    pipeline_notification = resources['pipelinenoti']['Properties']

    target = pipeline_notification["Targets"][0]

    assert resources["pipelinenoti"]["Type"] == "AWS::CodeStarNotifications::NotificationRule"
    assert target["TargetAddress"] == "arn:aws:chatbot::111111111111:chat-configuration/slack-channel/fake-config"
    assert target["TargetType"] == "AWSChatbotSlack"
    assert pipeline_notification["EventTypeIds"] == [
            "codepipeline-pipeline-stage-execution-succeeded",
            "codepipeline-pipeline-stage-execution-failed",
            "codepipeline-pipeline-pipeline-execution-started",
            "codepipeline-pipeline-pipeline-execution-failed",
            "codepipeline-pipeline-pipeline-execution-succeeded",
            "codepipeline-pipeline-manual-approval-needed",
            "codepipeline-pipeline-manual-approval-succeeded"
         ]
    assert pipeline_notification["DetailType"] == "FULL"

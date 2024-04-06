# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

# pylint: skip-file

from mock import patch
from cdk_constructs.adf_codepipeline import Action
from adf_codepipeline_test_constants import BASE_MAP_PARAMS

@patch('cdk_constructs.adf_codepipeline._codepipeline.CfnPipeline.ActionDeclarationProperty')
@patch('cdk_constructs.adf_codepipeline.Action._get_output_artifacts')
@patch('cdk_constructs.adf_codepipeline.Action._get_input_artifacts')
def test_generates_with_input_and_output_artifacts_when_given(input_mock, output_mock, action_decl_mock):
    action_decl_mock.side_effect = lambda **x: x
    mocked_input_value = 'InputArtifacts'
    mocked_output_value = 'OutputArtifacts'
    input_mock.return_value = mocked_input_value
    output_mock.return_value = mocked_output_value
    action = Action(
        map_params=BASE_MAP_PARAMS,
        category='Build',
        provider='CodeBuild',
    )
    assert action.config['input_artifacts'] == mocked_input_value
    assert action.config['output_artifacts'] == mocked_output_value


@patch('cdk_constructs.adf_codepipeline._codepipeline.CfnPipeline.ActionDeclarationProperty')
@patch('cdk_constructs.adf_codepipeline.Action._get_output_artifacts')
@patch('cdk_constructs.adf_codepipeline.Action._get_input_artifacts')
def test_generates_without_input_and_output_artifacts(input_mock, output_mock, action_decl_mock):
    action_decl_mock.side_effect = lambda **x: x
    mocked_value = None
    input_mock.return_value = mocked_value
    output_mock.return_value = mocked_value
    action = Action(
        map_params=BASE_MAP_PARAMS,
        category='Build',
        provider='CodeBuild',
    )
    assert 'input_artifacts' not in action.config
    assert 'output_artifacts' not in action.config

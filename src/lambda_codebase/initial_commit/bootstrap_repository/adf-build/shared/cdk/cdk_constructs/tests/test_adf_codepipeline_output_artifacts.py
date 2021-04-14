# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

# pylint: skip-file

from mock import patch
from copy import deepcopy
from cdk_constructs.adf_codepipeline import Action
from aws_cdk import ( aws_codepipeline )
from adf_codepipeline_test_constants import BASE_MAP_PARAMS


@patch('cdk_constructs.adf_codepipeline._codepipeline.CfnPipeline.ActionDeclarationProperty')
@patch('cdk_constructs.adf_codepipeline.Action._get_base_output_artifact_name')
def test_get_output_artifacts_no_base_output(base_output_name_mock, action_decl_mock):
    action_decl_mock.side_effect = lambda **x: x
    base_output_name_mock.return_value = ''
    action = Action(
        map_params=BASE_MAP_PARAMS,
        category='Build',
        provider='CodeBuild',
    )
    assert not 'output_artifacts' in action.config


@patch('cdk_constructs.adf_codepipeline._codepipeline.CfnPipeline.ActionDeclarationProperty')
@patch('cdk_constructs.adf_codepipeline.Action._get_base_output_artifact_name')
def test_get_output_artifacts_with_base_output(base_output_name_mock, action_decl_mock):
    action_decl_mock.side_effect = lambda **x: x
    base_output_name_mocked_value = 'BaseOutputName'
    base_output_name_mock.return_value = base_output_name_mocked_value
    action = Action(
        map_params=BASE_MAP_PARAMS,
        category='Build',
        provider='CodeBuild',
    )
    assert action.config['output_artifacts'] == [
        aws_codepipeline.CfnPipeline.OutputArtifactProperty(
            name=base_output_name_mocked_value,
        )
    ]


@patch('cdk_constructs.adf_codepipeline._codepipeline.CfnPipeline.ActionDeclarationProperty')
def test_get_base_output_artifact_name_source(action_decl_mock):
    action_decl_mock.side_effect = lambda **x: x
    action = Action(
        map_params=BASE_MAP_PARAMS,
        category='Source',
        provider='CodeCommit'
    )
    assert action._get_base_output_artifact_name() == 'output-source'


@patch('cdk_constructs.adf_codepipeline._codepipeline.CfnPipeline.ActionDeclarationProperty')
def test_get_base_output_artifact_name_build(action_decl_mock):
    action_decl_mock.side_effect = lambda **x: x
    action = Action(
        map_params=BASE_MAP_PARAMS,
        category='Build',
        provider='CodeBuild',
    )
    assert action._get_base_output_artifact_name() == '{0}-build'.format(BASE_MAP_PARAMS['name'])


@patch('cdk_constructs.adf_codepipeline._codepipeline.CfnPipeline.ActionDeclarationProperty')
def test_get_base_output_artifact_name_deploy_codebuild(action_decl_mock):
    action_decl_mock.side_effect = lambda **x: x
    action = Action(
        map_params=BASE_MAP_PARAMS,
        category='Deploy',
        provider='CodeBuild',
        target={
            'name': 'targetname',
            'id': 'someid',
        },
    )
    assert action._get_base_output_artifact_name() == ''


@patch('cdk_constructs.adf_codepipeline._codepipeline.CfnPipeline.ActionDeclarationProperty')
def test_get_base_output_artifact_name_deploy_cfn_without_outputs(action_decl_mock):
    action_decl_mock.side_effect = lambda **x: x
    action = Action(
        map_params=BASE_MAP_PARAMS,
        category='Deploy',
        provider='CloudFormation',
        target={
            'name': 'targetname',
            'id': 'someid',
        },
    )
    assert action._get_base_output_artifact_name() == ''


@patch('cdk_constructs.adf_codepipeline._codepipeline.CfnPipeline.ActionDeclarationProperty')
def test_get_base_output_artifact_name_deploy_cfn_with_outputs_csr(action_decl_mock):
    action_decl_mock.side_effect = lambda **x: x
    override_outputs_mocked_value = 'OverrideName'
    action = Action(
        map_params=BASE_MAP_PARAMS,
        category='Deploy',
        provider='CloudFormation',
        action_mode='CHANGE_SET_REPLACE',
        target={
            'name': 'targetname',
            'id': 'someid',
            'properties': {
                'outputs': override_outputs_mocked_value,
            },
        },
    )
    assert action._get_base_output_artifact_name() == ''


@patch('cdk_constructs.adf_codepipeline._codepipeline.CfnPipeline.ActionDeclarationProperty')
def test_get_base_output_artifact_name_deploy_cfn_with_outputs_cse(action_decl_mock):
    action_decl_mock.side_effect = lambda **x: x
    override_outputs_mocked_value = 'OverrideName'
    action = Action(
        map_params=BASE_MAP_PARAMS,
        category='Deploy',
        provider='CloudFormation',
        action_mode='CHANGE_SET_EXECUTE',
        target={
            'name': 'targetname',
            'id': 'someid',
            'properties': {
                'outputs': override_outputs_mocked_value,
            },
        },
    )
    assert action._get_base_output_artifact_name() == override_outputs_mocked_value

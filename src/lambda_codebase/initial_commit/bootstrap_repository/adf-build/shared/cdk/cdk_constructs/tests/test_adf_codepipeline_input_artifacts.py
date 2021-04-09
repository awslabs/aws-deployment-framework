# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

# pylint: skip-file

from mock import patch
from copy import deepcopy
from cdk_constructs.adf_codepipeline import Action
from aws_cdk import ( aws_codepipeline )
from adf_codepipeline_test_constants import BASE_MAP_PARAMS


@patch('cdk_constructs.adf_codepipeline._codepipeline.CfnPipeline.ActionDeclarationProperty')
def test_get_input_artifacts_no_build_deploy(action_decl_mock):
    action_decl_mock.side_effect = lambda **x: x
    for category in ['Approval', 'Source']:
        action = Action(
            map_params=BASE_MAP_PARAMS,
            category=category,
            provider='Manual' if category == 'Approval' else 'CodeCommit',
        )
        assert action._get_input_artifacts() == []


@patch('cdk_constructs.adf_codepipeline._codepipeline.CfnPipeline.ActionDeclarationProperty')
@patch('cdk_constructs.adf_codepipeline.Action._get_base_input_artifact_name')
def test_get_input_artifacts_build(base_input_name_mock, action_decl_mock):
    action_decl_mock.side_effect = lambda **x: x
    base_input_name_mocked_value = 'BaseInputName'
    base_input_name_mock.return_value = base_input_name_mocked_value
    action = Action(
        map_params=BASE_MAP_PARAMS,
        category='Build',
        provider='CodeBuild',
    )
    assert action.config['input_artifacts'] == [
        aws_codepipeline.CfnPipeline.InputArtifactProperty(
            name=base_input_name_mocked_value,
        )
    ]


@patch('cdk_constructs.adf_codepipeline._codepipeline.CfnPipeline.ActionDeclarationProperty')
@patch('cdk_constructs.adf_codepipeline.Action._get_base_input_artifact_name')
def test_get_input_artifacts_deploy_simple(base_input_name_mock, action_decl_mock):
    action_decl_mock.side_effect = lambda **x: x
    base_input_name_mocked_value = 'BaseInputName'
    base_input_name_mock.return_value = base_input_name_mocked_value
    action = Action(
        map_params=BASE_MAP_PARAMS,
        category='Deploy',
        provider='CodeBuild',
        target={
            'properties': {
                'param_overrides': [],
            },
        },
    )
    assert action.config['input_artifacts'] == [
        aws_codepipeline.CfnPipeline.InputArtifactProperty(
            name=base_input_name_mocked_value,
        )
    ]


@patch('cdk_constructs.adf_codepipeline._codepipeline.CfnPipeline.ActionDeclarationProperty')
@patch('cdk_constructs.adf_codepipeline.Action._get_base_input_artifact_name')
def test_get_input_artifacts_deploy_with_cb_param_overrides(base_input_name_mock, action_decl_mock):
    action_decl_mock.side_effect = lambda **x: x
    base_input_name_mocked_value = 'BaseInputName'
    base_input_name_mock.return_value = base_input_name_mocked_value
    override_mocked_value = 'OverrideName'
    action = Action(
        map_params=BASE_MAP_PARAMS,
        category='Deploy',
        provider='CodeBuild',
        target={
            'properties': {
                'param_overrides': [
                    {
                        'param': 'SomeParam',
                        'inputs': override_mocked_value,
                        'key_name': 'SomeKeyName',
                    },
                ],
            },
        },
    )
    assert action.config['input_artifacts'] == [
        aws_codepipeline.CfnPipeline.InputArtifactProperty(
            name=base_input_name_mocked_value,
        )
    ]


@patch('cdk_constructs.adf_codepipeline._codepipeline.CfnPipeline.ActionDeclarationProperty')
@patch('cdk_constructs.adf_codepipeline.Action._get_base_input_artifact_name')
def test_get_input_artifacts_deploy_with_cfn_param_overrides_is_cse(base_input_name_mock, action_decl_mock):
    action_decl_mock.side_effect = lambda **x: x
    base_input_name_mocked_value = 'BaseInputName'
    base_input_name_mock.return_value = base_input_name_mocked_value
    override_mocked_value = 'OverrideName'
    action = Action(
        map_params=BASE_MAP_PARAMS,
        category='Deploy',
        provider='CloudFormation',
        action_mode='CHANGE_SET_EXECUTE',
        target={
            'name': 'targetname',
            'id': 'someid',
            'properties': {
                'param_overrides': [
                    {
                        'param': 'SomeParam',
                        'inputs': override_mocked_value,
                        'key_name': 'SomeKeyName',
                    },
                ],
            },
        },
    )
    assert action.config['input_artifacts'] == [
        aws_codepipeline.CfnPipeline.InputArtifactProperty(
            name=base_input_name_mocked_value,
        )
    ]


@patch('cdk_constructs.adf_codepipeline._codepipeline.CfnPipeline.ActionDeclarationProperty')
@patch('cdk_constructs.adf_codepipeline.Action._get_base_input_artifact_name')
def test_get_input_artifacts_deploy_with_cfn_param_overrides_not_cse(base_input_name_mock, action_decl_mock):
    action_decl_mock.side_effect = lambda **x: x
    base_input_name_mocked_value = 'BaseInputName'
    base_input_name_mock.return_value = base_input_name_mocked_value
    override_mocked_value = 'OverrideName'
    action = Action(
        map_params=BASE_MAP_PARAMS,
        category='Deploy',
        provider='CloudFormation',
        action_mode='CHANGE_SET_REPLACE',
        target={
            'name': 'targetname',
            'id': 'someid',
            'properties': {
                'param_overrides': [
                    {
                        'param': 'SomeParam',
                        'inputs': override_mocked_value,
                        'key_name': 'SomeKeyName',
                    },
                ],
            },
        },
    )
    assert action.config['input_artifacts'] == [
        aws_codepipeline.CfnPipeline.InputArtifactProperty(
            name=base_input_name_mocked_value,
        ),
        aws_codepipeline.CfnPipeline.InputArtifactProperty(
            name=override_mocked_value,
        )
    ]


@patch('cdk_constructs.adf_codepipeline._codepipeline.CfnPipeline.ActionDeclarationProperty')
def test_get_base_input_artifact_name_build_enabled(action_decl_mock):
    action_decl_mock.side_effect = lambda **x: x
    action = Action(
        map_params=BASE_MAP_PARAMS,
        category='Build',
        provider='CodeBuild'
    )
    assert action._get_base_input_artifact_name() == 'output-source'


@patch('cdk_constructs.adf_codepipeline._codepipeline.CfnPipeline.ActionDeclarationProperty')
def test_get_base_input_artifact_name_deploy_build_disabled(action_decl_mock):
    action_decl_mock.side_effect = lambda **x: x
    map_params = deepcopy(BASE_MAP_PARAMS)
    map_params['default_providers']['build']['enabled'] = False
    action = Action(
        map_params=map_params,
        category='Deploy',
        provider='CodeBuild',
        target={
            'name': 'targetname',
            'id': 'someid',
        },
    )
    assert action._get_base_input_artifact_name() == 'output-source'


@patch('cdk_constructs.adf_codepipeline._codepipeline.CfnPipeline.ActionDeclarationProperty')
def test_get_base_input_artifact_name_deploy_build_enabled(action_decl_mock):
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
    assert action._get_base_input_artifact_name() == '{0}-build'.format(BASE_MAP_PARAMS['name'])

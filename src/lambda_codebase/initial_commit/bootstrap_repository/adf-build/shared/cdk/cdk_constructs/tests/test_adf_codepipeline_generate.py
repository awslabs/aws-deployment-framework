# Copyright Amazon.com Inc. or its affiliates.
# SPDX-License-Identifier: MIT-0

# pylint: skip-file

from mock import patch
from copy import deepcopy
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
    assert not 'input_artifacts' in action.config
    assert not 'output_artifacts' in action.config


@patch('cdk_constructs.adf_codepipeline._codepipeline.CfnPipeline.ActionDeclarationProperty')
def test_source_account_id_defaults_to_deployment_account_when_omitted(action_decl_mock):
    action_decl_mock.side_effect = lambda **x: x
    map_params = deepcopy(BASE_MAP_PARAMS)
    del map_params['default_providers']['source']['properties']['account_id']
    assert 'scm/default_scm_codecommit_account_id' not in map_params
    action = Action(
        map_params=map_params,
        category='Source',
        provider='CodeCommit',
    )
    # ACCOUNT_ID is set to '111111111111' (str) in tox.ini, which is used as
    # the ADF_DEFAULT_SCM_CODECOMMIT_ACCOUNT_ID fallback.
    assert action._get_role_account_id() == '111111111111'
    assert action.config['role_arn'] == (
        'arn:aws:iam::111111111111:role/adf-codecommit-role'
    )


@patch('cdk_constructs.adf_codepipeline._codepipeline.CfnPipeline.ActionDeclarationProperty')
def test_source_account_id_uses_explicit_account_id_when_provided(action_decl_mock):
    action_decl_mock.side_effect = lambda **x: x
    map_params = deepcopy(BASE_MAP_PARAMS)
    map_params['default_providers']['source']['properties']['account_id'] = '222222222222'
    action = Action(
        map_params=map_params,
        category='Source',
        provider='CodeCommit',
    )
    assert action._get_role_account_id() == '222222222222'
    assert action.config['role_arn'] == (
        'arn:aws:iam::222222222222:role/adf-codecommit-role'
    )


@patch('cdk_constructs.adf_codepipeline._codepipeline.CfnPipeline.ActionDeclarationProperty')
def test_source_account_id_uses_default_scm_codecommit_account_id_override(action_decl_mock):
    action_decl_mock.side_effect = lambda **x: x
    map_params = deepcopy(BASE_MAP_PARAMS)
    del map_params['default_providers']['source']['properties']['account_id']
    map_params['scm/default_scm_codecommit_account_id'] = '333333333333'
    action = Action(
        map_params=map_params,
        category='Source',
        provider='CodeCommit',
    )
    assert action._get_role_account_id() == '333333333333'
    assert action.config['role_arn'] == (
        'arn:aws:iam::333333333333:role/adf-codecommit-role'
    )

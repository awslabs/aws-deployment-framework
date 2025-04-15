# Copyright Amazon.com Inc. or its affiliates.
# SPDX-License-Identifier: MIT-0

# pylint: skip-file

import json
import os
from boto3.session import Session
from pytest import fixture, raises
from mock import call, Mock
from copy import deepcopy
from .stubs import stub_iam
from lambda_codebase.iam_cfn_deploy_role_policy import IAMCfnDeployRolePolicy

REGION = os.getenv("AWS_REGION", "us-east-1")
PARTITION = Session().get_partition_for_region(REGION)

@fixture
def iam_client():
    client = Mock()
    client.get_role_policy.side_effect = (
        lambda **kwargs: deepcopy(stub_iam.get_role_policy)
    )
    return client


def test_fetch_policy_document(iam_client):
    role_name = 'RoleName'
    policy_name = 'PolicyName'

    instance = IAMCfnDeployRolePolicy(iam_client, role_name, policy_name)

    iam_client.get_role_policy.assert_called_once_with(
        RoleName=role_name,
        PolicyName=policy_name,
    )

    assert instance.client == iam_client
    assert instance.role_name == role_name
    assert instance.policy_name == policy_name
    assert instance.policy_changed is False
    assert instance.policy_document == (
        stub_iam.get_role_policy['PolicyDocument']
    )


def test_grant_access_to_s3_buckets_no_S3_statement(iam_client):
    instance = IAMCfnDeployRolePolicy(iam_client, 'ExRoleName', 'ExPolicyName')
    del instance.policy_document['Statement'][1]
    policy_doc_before = deepcopy(instance.policy_document)

    instance.grant_access_to_s3_buckets(['new_bucket'])

    assert instance.policy_changed is False
    assert instance.policy_document == policy_doc_before


def test_grant_access_to_s3_buckets_multiple_S3_statement(iam_client):
    instance = IAMCfnDeployRolePolicy(iam_client, 'ExRoleName', 'ExPolicyName')
    instance.policy_document['Statement'] = [
        instance.policy_document['Statement'][0],
        instance.policy_document['Statement'][1],
        instance.policy_document['Statement'][1],
    ]
    correct_error_message = (
        'Found multiple S3 statements in Role ExRoleName Policy ExPolicyName.'
    )

    with raises(Exception) as excinfo:
        instance.grant_access_to_s3_buckets(['new_bucket'])

    error_message = str(excinfo.value)
    assert error_message.find(correct_error_message) >= 0


def test_grant_access_to_s3_buckets_empty_list(iam_client):
    instance = IAMCfnDeployRolePolicy(iam_client, 'RoleName', 'PolicyName')
    policy_doc_before = deepcopy(instance.policy_document)

    instance.grant_access_to_s3_buckets([])

    assert instance.policy_changed is False
    assert instance.policy_document == policy_doc_before


def test_grant_access_to_s3_buckets_exists_already(iam_client):
    instance = IAMCfnDeployRolePolicy(iam_client, 'RoleName', 'PolicyName')
    policy_doc_before = deepcopy(instance.policy_document)

    instance.grant_access_to_s3_buckets(['existing_bucket'])

    assert instance.policy_changed is False
    assert instance.policy_document == policy_doc_before


def test_grant_access_to_s3_buckets_new_bucket_single_resource(iam_client):
    instance = IAMCfnDeployRolePolicy(iam_client, 'RoleName', 'PolicyName')
    instance.policy_document['Statement'][1]['Resource'] = (
        instance.policy_document['Statement'][1]['Resource'][0]
    )
    policy_doc_before = deepcopy(instance.policy_document)

    instance.grant_access_to_s3_buckets(['new_bucket'])

    assert instance.policy_changed is True
    assert instance.policy_document != policy_doc_before
    assert instance.policy_document['Statement'][0] == (
        policy_doc_before['Statement'][0]
    )
    assert instance.policy_document['Statement'][1]['Sid'] == (
        policy_doc_before['Statement'][1]['Sid']
    )
    assert instance.policy_document['Statement'][1]['Effect'] == (
        policy_doc_before['Statement'][1]['Effect']
    )
    assert instance.policy_document['Statement'][1]['Action'] == (
        policy_doc_before['Statement'][1]['Action']
    )
    assert instance.policy_document['Statement'][1]['Resource'] == [
        policy_doc_before['Statement'][1]['Resource'],
        f'arn:{PARTITION}:s3:::new_bucket',
        f'arn:{PARTITION}:s3:::new_bucket/*',
    ]
    assert instance.policy_document['Statement'][2] == (
        policy_doc_before['Statement'][2]
    )


def test_grant_access_to_s3_buckets_new_buckets(iam_client):
    instance = IAMCfnDeployRolePolicy(iam_client, 'RoleName', 'PolicyName')
    policy_doc_before = deepcopy(instance.policy_document)

    instance.grant_access_to_s3_buckets([
        'existing_bucket',
        'new_bucket',
        'another_new_bucket',
    ])

    assert instance.policy_changed is True
    assert instance.policy_document != policy_doc_before
    assert instance.policy_document['Statement'][0] == (
        policy_doc_before['Statement'][0]
    )
    assert instance.policy_document['Statement'][1]['Sid'] == (
        policy_doc_before['Statement'][1]['Sid']
    )
    assert instance.policy_document['Statement'][1]['Effect'] == (
        policy_doc_before['Statement'][1]['Effect']
    )
    assert instance.policy_document['Statement'][1]['Action'] == (
        policy_doc_before['Statement'][1]['Action']
    )
    assert instance.policy_document['Statement'][1]['Resource'] == [
        policy_doc_before['Statement'][1]['Resource'][0],
        policy_doc_before['Statement'][1]['Resource'][1],
        f'arn:{PARTITION}:s3:::new_bucket',
        f'arn:{PARTITION}:s3:::new_bucket/*',
        f'arn:{PARTITION}:s3:::another_new_bucket',
        f'arn:{PARTITION}:s3:::another_new_bucket/*',
    ]
    assert instance.policy_document['Statement'][2] == (
        policy_doc_before['Statement'][2]
    )


def test_grant_access_to_kms_keys_empty_list(iam_client):
    instance = IAMCfnDeployRolePolicy(iam_client, 'RoleName', 'PolicyName')
    policy_doc_before = deepcopy(instance.policy_document)

    instance.grant_access_to_kms_keys([])

    assert instance.policy_changed is False
    assert instance.policy_document == policy_doc_before


def test_grant_access_to_kms_keys_exists_already(iam_client):
    instance = IAMCfnDeployRolePolicy(iam_client, 'RoleName', 'PolicyName')
    policy_doc_before = deepcopy(instance.policy_document)

    instance.grant_access_to_kms_keys([
        policy_doc_before['Statement'][0]['Resource'],
    ])

    assert instance.policy_changed is False
    assert instance.policy_document == policy_doc_before


def test_grant_access_to_kms_keys_new_key_single_resource(iam_client):
    instance = IAMCfnDeployRolePolicy(iam_client, 'RoleName', 'PolicyName')
    instance.policy_document['Statement'][1]['Resource'] = (
        instance.policy_document['Statement'][1]['Resource'][0]
    )
    policy_doc_before = deepcopy(instance.policy_document)
    test_region = "cn-north-1" if PARTITION == "aws-cn" else "eu-west-1"
    new_key_arn = f'arn:{PARTITION}:kms:{test_region}:111111111111:key/new_key'
    instance.grant_access_to_kms_keys([
        new_key_arn,
    ])

    assert instance.policy_changed is True
    assert instance.policy_document != policy_doc_before
    assert instance.policy_document['Statement'][0]['Sid'] == (
        policy_doc_before['Statement'][0]['Sid']
    )
    assert instance.policy_document['Statement'][0]['Effect'] == (
        policy_doc_before['Statement'][0]['Effect']
    )
    assert instance.policy_document['Statement'][0]['Action'] == (
        policy_doc_before['Statement'][0]['Action']
    )
    assert instance.policy_document['Statement'][0]['Resource'] == [
        policy_doc_before['Statement'][0]['Resource'],
        new_key_arn,
    ]
    assert instance.policy_document['Statement'][1] == (
        policy_doc_before['Statement'][1]
    )
    assert instance.policy_document['Statement'][2] == (
        policy_doc_before['Statement'][2]
    )


def test_grant_access_to_kms_keys_new_keys(iam_client):
    instance = IAMCfnDeployRolePolicy(iam_client, 'RoleName', 'PolicyName')
    existing_key_arn_1 = instance.policy_document['Statement'][0]['Resource']
    existing_key_arn_2 = f"{existing_key_arn_1}_no2"
    instance.policy_document['Statement'][0]['Resource'] = [
        existing_key_arn_1,
        existing_key_arn_2,
    ]
    policy_doc_before = deepcopy(instance.policy_document)

    new_key_arn_1 = f'arn:{PARTITION}:kms:eu-west-1:111111111111:key/new_key_no_1'
    new_key_arn_2 = f'arn:{PARTITION}:kms:eu-west-1:111111111111:key/new_key_no_2'
    instance.grant_access_to_kms_keys([
        new_key_arn_1,
        existing_key_arn_1,
        new_key_arn_2,
        existing_key_arn_2,
    ])

    assert instance.policy_changed is True
    assert instance.policy_document != policy_doc_before
    assert instance.policy_document['Statement'][0]['Sid'] == (
        policy_doc_before['Statement'][0]['Sid']
    )
    assert instance.policy_document['Statement'][0]['Effect'] == (
        policy_doc_before['Statement'][0]['Effect']
    )
    assert instance.policy_document['Statement'][0]['Action'] == (
        policy_doc_before['Statement'][0]['Action']
    )
    assert instance.policy_document['Statement'][0]['Resource'] == [
        existing_key_arn_1,
        existing_key_arn_2,
        new_key_arn_1,
        new_key_arn_2,
    ]
    assert instance.policy_document['Statement'][1] == (
        policy_doc_before['Statement'][1]
    )
    assert instance.policy_document['Statement'][2] == (
        policy_doc_before['Statement'][2]
    )


def test_save_no_changes(iam_client):
    instance = IAMCfnDeployRolePolicy(iam_client, 'RoleName', 'PolicyName')

    assert instance.policy_changed is False
    instance.save()

    iam_client.put_role_policy.assert_not_called()
    assert instance.policy_changed is False


def test_save_with_changes(iam_client):
    role_name = 'RoleName'
    policy_name = 'PolicyName'
    instance = IAMCfnDeployRolePolicy(iam_client, role_name, policy_name)
    instance.grant_access_to_s3_buckets(['new_bucket'])

    assert instance.policy_changed is True
    instance.save()

    iam_client.put_role_policy.assert_called_once_with(
        RoleName=instance.role_name,
        PolicyName=instance.policy_name,
        PolicyDocument=json.dumps(instance.policy_document),
    )
    assert instance.policy_changed is False


def test_save_twice(iam_client):
    role_name = 'RoleName'
    policy_name = 'PolicyName'
    instance = IAMCfnDeployRolePolicy(iam_client, role_name, policy_name)
    instance.grant_access_to_s3_buckets(['new_bucket'])

    assert instance.policy_changed is True
    instance.save()
    instance.save()

    iam_client.put_role_policy.assert_called_once_with(
        RoleName=instance.role_name,
        PolicyName=instance.policy_name,
        PolicyDocument=json.dumps(instance.policy_document),
    )
    assert instance.policy_changed is False


def test_update_iam_role_policies_empty_lists(iam_client):
    s3_bucket_names = []
    kms_key_arns = []
    role_policies = {
        'role_1': [
            'policy_r1_1',
            'policy_r1_2',
        ],
        'role_2': [
            'policy_r2_1',
        ],
    }

    IAMCfnDeployRolePolicy.update_iam_role_policies(
        iam_client,
        s3_bucket_names,
        kms_key_arns,
        role_policies,
    )

    assert iam_client.get_role_policy.call_count == 3
    iam_client.get_role_policy.assert_has_calls([
        call(RoleName='role_1', PolicyName='policy_r1_1'),
        call(RoleName='role_1', PolicyName='policy_r1_2'),
        call(RoleName='role_2', PolicyName='policy_r2_1'),
    ])
    iam_client.put_role_policy.assert_not_called()


def test_update_iam_role_policies_updated(iam_client):
    s3_bucket_names = ['new_bucket']
    kms_key_arns = []
    role_policies = {
        'role_1': [
            'policy_r1_1',
            'policy_r1_2',
        ],
        'role_2': [
            'policy_r2_1',
        ],
    }
    policy_doc = deepcopy(stub_iam.get_role_policy['PolicyDocument'])
    policy_doc['Statement'][1]['Resource'] = [
        policy_doc['Statement'][1]['Resource'][0],
        policy_doc['Statement'][1]['Resource'][1],
        f'arn:{PARTITION}:s3:::new_bucket',
        f'arn:{PARTITION}:s3:::new_bucket/*',
    ]
    policy_doc_json = json.dumps(policy_doc)

    IAMCfnDeployRolePolicy.update_iam_role_policies(
        iam_client,
        s3_bucket_names,
        kms_key_arns,
        role_policies,
    )

    assert iam_client.get_role_policy.call_count == 3
    iam_client.get_role_policy.assert_has_calls([
        call(RoleName='role_1', PolicyName='policy_r1_1'),
        call(RoleName='role_1', PolicyName='policy_r1_2'),
        call(RoleName='role_2', PolicyName='policy_r2_1'),
    ])

    assert iam_client.put_role_policy.call_count == 3
    iam_client.put_role_policy.assert_has_calls([
        call(
            RoleName='role_1',
            PolicyName='policy_r1_1',
            PolicyDocument=policy_doc_json,
        ),
        call(
            RoleName='role_1',
            PolicyName='policy_r1_2',
            PolicyDocument=policy_doc_json,
        ),
        call(
            RoleName='role_2',
            PolicyName='policy_r2_1',
            PolicyDocument=policy_doc_json,
        )
    ])

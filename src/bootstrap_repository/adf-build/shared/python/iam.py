# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""IAM module used throughout the ADF
"""

import json


class IAM:
    """Class used for modeling IAM
    """

    def __init__(self, role):
        self.client = role.client('iam')
        self.role_name = None
        self.policy_name = None
        self.policy = None

    def update_iam_target_account_roles(
            self,
            kms_key_arn,
            target_role_policies
        ):
        for role_name, policy_name in target_role_policies.items():
            self._fetch_policy_document(role_name, policy_name)
            self._update_iam_cfn(kms_key_arn)
            self._put_role_policy()

    def update_iam_roles(
            self,
            s3_bucket,
            kms_key_arn,
            role_policies
        ):
        for role_name, policy_name in role_policies.items():
            self._fetch_policy_document(role_name, policy_name)
            self._update_iam_policy_bucket(s3_bucket)
            self._update_iam_cfn(kms_key_arn)
            self._put_role_policy()

    def _get_policy(self):
        return self.policy

    def _set_policy(self, policy):
        self.policy = policy

    def _set_role_name(self, role_name):
        self.role_name = role_name

    def _set_policy_name(self, policy_name):
        self.policy_name = policy_name

    def _fetch_policy_document(self, role_name, policy_name):
        self._set_role_name(role_name)
        self._set_policy_name(policy_name)

        policy = self.client.get_role_policy(
            RoleName=role_name,
            PolicyName=policy_name
        )

        self._set_policy(policy['PolicyDocument'])

    def _put_role_policy(self):
        return self.client.put_role_policy(
            RoleName=self.role_name,
            PolicyName=self.policy_name,
            PolicyDocument=json.dumps(self._get_policy())
        )

    def _update_iam_policy_bucket(self, bucket_name):
        """
        Updates the S3 Bucket Policy to allow the target account access
        to deployment resources
        """
        _policy = self._get_policy()
        for statement in _policy.get('Statement', None):
            if statement['Sid'] == 'S3':
                if "arn:aws:s3:::{0}".format(
                        bucket_name) not in statement['Resource']:
                    statement['Resource'].append(
                        "arn:aws:s3:::{0}".format(bucket_name))
                    statement['Resource'].append(
                        "arn:aws:s3:::{0}/*".format(bucket_name))

        self._set_policy(_policy)

    def _update_iam_cfn(
            self, kms_key_arn):
        """
        Updates the Cloudformation Deployment Role to allow use of the KMS Key
        """
        _policy = self._get_policy()

        for statement in _policy.get('Statement', None):
            if statement['Sid'] == 'KMS':
                if kms_key_arn not in statement['Resource']:
                    try:
                        statement['Resource'].append(kms_key_arn)
                    except AttributeError:
                        statement['Resource'] = [statement['Resource']]
                        statement['Resource'].append(kms_key_arn)

        self._set_policy(_policy)

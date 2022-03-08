# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""IAM module used throughout the ADF
"""

import json
import os

from logger import configure_logger
from partition import get_partition

LOGGER = configure_logger(__name__)
REGION_DEFAULT = os.getenv('AWS_REGION')
PARTITION = get_partition(REGION_DEFAULT)


class IAM:
    """Class used for modeling IAM."""

    def __init__(self, client):
        self.client = client
        self.role_name = None
        self.policy_name = None
        self.policy = None

    def update_iam_roles(
            self,
            s3_buckets,
            kms_key_arns,
            role_policies
        ):
        if not isinstance(s3_buckets, list):
            s3_buckets = [s3_buckets]
        if not isinstance(kms_key_arns, list):
            kms_key_arns = [kms_key_arns]

        for role_name, policy_name in role_policies.items():
            self._fetch_policy_document(role_name, policy_name)
            for s3_bucket in s3_buckets:
                self._update_iam_policy_bucket(s3_bucket)
            for kms_key_arn in kms_key_arns:
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
        LOGGER.debug('Fetching policy %s for role %s', policy_name, role_name)
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
                LOGGER.debug('calling _update_iam_policy_bucket for bucket_name %s', bucket_name)
                if f"arn:{PARTITION}:s3:::{bucket_name}" not in statement['Resource']:
                    LOGGER.info('Updating Role %s to access %s', self.role_name, bucket_name)
                    statement['Resource'].append(f"arn:{PARTITION}:s3:::{bucket_name}")
                    statement['Resource'].append(f"arn:{PARTITION}:s3:::{bucket_name}/*")

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
                    LOGGER.info('Updating Role %s to be able to access %s', self.role_name, kms_key_arn)
                    try:
                        statement['Resource'].append(kms_key_arn)
                    except AttributeError:
                        statement['Resource'] = [statement['Resource']]
                        statement['Resource'].append(kms_key_arn)

        self._set_policy(_policy)

# Copyright Amazon.com Inc. or its affiliates.
# SPDX-License-Identifier: MIT-0

"""
CloudFormation Deployment Role Policy used to manage cross account
access.
"""

import json
import os

from logger import configure_logger
from partition import get_partition

LOGGER = configure_logger(__name__)
REGION_DEFAULT = os.getenv('AWS_REGION')
PARTITION = get_partition(REGION_DEFAULT)


class IAMCfnDeployRolePolicy:
    """
    Class to manage an CloudFormation Deployment IAM Role Policy.
    Used to update the cross-account CloudFormation Deployment role.
    """

    def __init__(self, client, role_name, policy_name):
        """
        Create a new IAM Role Policy instance.

        Args:
            client (boto3.IAM.client): The boto3 IAM client.
            role_name (str):           The role name.
            policy_name (str):         The policy name.
            policy_document (dict):    The policy document.
        """
        self.client = client
        self.role_name = role_name
        self.policy_name = policy_name

        LOGGER.debug('Fetching policy %s for role %s', policy_name, role_name)
        role_policy_result = client.get_role_policy(
            RoleName=role_name,
            PolicyName=policy_name,
        )
        self.policy_changed = False
        self.policy_document = role_policy_result['PolicyDocument']

    def _get_statement(self, statement_id):
        s3_statements = list(filter(
            lambda stmt: stmt['Sid'] == statement_id,
            self.policy_document.get('Statement', {})
        ))
        if len(s3_statements) == 1:
            return s3_statements[0]

        if len(s3_statements) > 1:
            raise AssertionError(
                f'Found multiple {statement_id} statements in '
                f'Role {self.role_name} Policy {self.policy_name}.'
            )
        return None

    def grant_access_to_s3_buckets(self, bucket_names):
        """
        Updates the IAM Role Policy to grant access to the specified S3 Bucket.
        Allowing target account access to the deployment resources.

        Args:
            bucket_name (list[str]): The bucket names to grant access to.
        """
        LOGGER.debug(
            'calling grant_s3_buckets_access for bucket_names %s',
            bucket_names,
        )
        if len(bucket_names) == 0:
            return

        statement = self._get_statement('S3')
        if statement is None:
            return

        for bucket_name in bucket_names:
            if f"arn:{PARTITION}:s3:::{bucket_name}" in statement['Resource']:
                # The bucket is in the resource statement already, great!
                continue

            LOGGER.info(
                'Updating Role %s policy %s to access S3://%s',
                self.role_name,
                self.policy_name,
                bucket_name,
            )
            self.policy_changed = True
            if not isinstance(statement['Resource'], list):
                statement['Resource'] = [statement['Resource']]
            statement['Resource'].append(
                f"arn:{PARTITION}:s3:::{bucket_name}",
            )
            statement['Resource'].append(
                f"arn:{PARTITION}:s3:::{bucket_name}/*",
            )

    def grant_access_to_kms_keys(self, kms_key_arns):
        """
        Updates the CloudFormation Deployment Role to allow use of the
        given KMS Key Arns.

        Args:
            kms_key_arns (list[str]): The KMS Key Arns to grant access to.
        """
        LOGGER.debug(
            'calling grant_usage_on_kms_keys for key arns %s',
            kms_key_arns,
        )
        if len(kms_key_arns) == 0:
            return

        statement = self._get_statement('KMS')
        if statement is None:
            return

        for kms_key_arn in kms_key_arns:
            if kms_key_arn in statement['Resource']:
                # The Key is in the resource statement already, great!
                continue
            LOGGER.info(
                'Updating Role %s Policy %s to be able to access %s',
                self.role_name,
                self.policy_name,
                kms_key_arn,
            )
            self.policy_changed = True
            if not isinstance(statement['Resource'], list):
                statement['Resource'] = [statement['Resource']]
            statement['Resource'].append(kms_key_arn)

    def save(self):
        """
        Save the role policy if it was modified.
        """
        if self.policy_changed is False:
            LOGGER.debug(
                "Request to save the policy %s, while no changes were made.",
                self.policy_name,
            )
            return
        self.client.put_role_policy(
            RoleName=self.role_name,
            PolicyName=self.policy_name,
            PolicyDocument=json.dumps(self.policy_document)
        )
        self.policy_changed = False

    @staticmethod
    def update_iam_role_policies(
        client,
        s3_bucket_names,
        kms_key_arns,
        role_policies,
    ):
        """
        Update the IAM CloudFormation Deployment Role Policies to grant
        access to the given list of S3 buckets and KMS Keys.

        Args:
            client (boto3.IAM.client): The IAM boto3 client.

            s3_bucket_names (list[str]): The names of the S3 buckets that
                should be granted access to.

            kms_key_arns (list[str]): The Arns of the KMS Keys that should be
                granted access to.

            role_policies (dict[str, list[str]): The role policies to update.
                Where the key is the role name and the value captures the list
                of policies names to update.
        """
        for role_name, policy_names in role_policies.items():
            for policy_name in policy_names:
                iam_role_policy = IAMCfnDeployRolePolicy(
                    client,
                    role_name,
                    policy_name,
                )
                iam_role_policy.grant_access_to_s3_buckets(s3_bucket_names)
                iam_role_policy.grant_access_to_kms_keys(kms_key_arns)
                iam_role_policy.save()

# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""KMS module used throughout the ADF
"""

import json


class KMS:
    """Class used for modeling KMS
    """

    def __init__(self, region, role, key_arn, account_id):
        self.client = role.client('kms', region_name=region)
        self.policy_name = 'default'
        self.account_id = account_id
        self.policy = None
        self.key_id = key_arn.split('/')[-1]

    def enable_cross_account_access(self):
        self._fetch_key_policy()
        self._update_key_policy()
        self._put_key_policy()

    def _set_key_policy(self, policy):
        self.policy = policy

    def _get_key_policy(self):
        return self.policy

    def _fetch_key_policy(self):
        policy = self.client.get_key_policy(
            KeyId=self.key_id,
            PolicyName=self.policy_name
        )
        self._set_key_policy(
            json.loads(
                json.dumps(
                    policy.get('Policy')
                )
            )
        )

    def _put_key_policy(self):
        return self.client.put_key_policy(
            KeyId=self.key_id,
            PolicyName=self.policy_name,
            Policy=json.dumps(self._get_key_policy()),
            BypassPolicyLockoutSafetyCheck=True
        )

    def _update_key_policy(self):
        policy = json.loads(self._get_key_policy())

        try:
            policy['Statement'][-1]['Principal']['AWS'].append(
                'arn:aws:iam::{0}:root'.format(self.account_id)
            )
        except AttributeError:
            policy['Statement'][-1]['Principal']['AWS'] = [
                policy['Statement'][-1]['Principal']['AWS']]

            policy['Statement'][-1]['Principal']['AWS'].append(
                'arn:aws:iam::{0}:root'.format(self.account_id))

        self._set_key_policy(policy)

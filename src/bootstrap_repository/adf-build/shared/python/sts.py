# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""STS module used throughout the ADF
"""

import boto3
from logger import configure_logger

LOGGER = configure_logger(__name__)


class STS:
    """Class used for modeling STS
    """

    def __init__(self):
        self.client = boto3.client('sts')

    def assume_cross_account_role(self, role_arn, role_session_name):
        """Assumes a role in another account and returns the temporary credentials
        """

        sts_response = self.client.assume_role(
            RoleArn=role_arn, RoleSessionName=role_session_name
        )

        return boto3.Session(
            aws_access_key_id=sts_response['Credentials']['AccessKeyId'],
            aws_secret_access_key=sts_response['Credentials']['SecretAccessKey'],
            aws_session_token=sts_response['Credentials']['SessionToken'])

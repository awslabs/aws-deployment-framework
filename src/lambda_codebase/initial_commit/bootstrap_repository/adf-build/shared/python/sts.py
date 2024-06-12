# Copyright Amazon.com Inc. or its affiliates.
# SPDX-License-Identifier: MIT-0

"""STS module used throughout the ADF
"""

import boto3
import botocore
from logger import configure_logger

LOGGER = configure_logger(__name__)
ACCESS_DENIED_ERROR_CODE = "AccessDenied"
ADF_JUMP_ROLE_NAME = (
    "adf/account-bootstrapping/jump/"
    "adf-bootstrapping-cross-account-jump-role"
)
ADF_BOOTSTRAP_UPDATE_DEPLOYMENT_ROLE_NAME = (
    "adf/bootstrap/"
    "adf-bootstrap-update-deployment-role"
)


class STS:
    """Class used for modeling STS
    """

    def __init__(self, client=None):
        self.client = client or boto3.client('sts')

    def assume_cross_account_role(self, role_arn, role_session_name):
        """Assumes a role in another account and returns the temporary credentials
        """
        LOGGER.debug(
            "Assuming into %s with session name: %s",
            role_arn,
            role_session_name,
        )

        sts_response = self.client.assume_role(
            RoleArn=role_arn, RoleSessionName=role_session_name
        )
        LOGGER.info(
            "Assumed into %s with session name: %s",
            role_arn,
            role_session_name,
        )

        return boto3.Session(
            aws_access_key_id=sts_response['Credentials']['AccessKeyId'],
            aws_secret_access_key=sts_response['Credentials']['SecretAccessKey'],
            aws_session_token=sts_response['Credentials']['SessionToken'],
        )

    @staticmethod
    def _build_role_arn(
        partition,
        account_id,
        role_name,
    ):
        return f"arn:{partition}:iam::{account_id}:role/{role_name}"

    def assume_bootstrap_deployment_role(
        self,
        partition,
        management_account_id,
        account_id,
        privileged_role_name,
        role_session_name,
    ):
        """
        Assuming into the JumpRole first, while using the role credentials
        it will attempt to assume into the privileged access role first.

        If access to the privileged cross-account access role is denied,
        the Access Denied error is caught. In this case, it will attempt to
        assume into the ADF Bootstrap Update Deployment role instead.

        The privileged cross-account access role is only granted access to if
        the account is not bootstrapped by ADF yet. Or when ADF is configured
        with a GrantOrgWidePrivilegedBootstrapAccessUntil date/time that is in
        the future.
        """
        LOGGER.info(
            "Using ADF Account-Bootstrapping Jump Role to assume "
            "into account %s",
            account_id,
        )
        jump_role_session = self.assume_cross_account_role(
            STS._build_role_arn(
                partition,
                management_account_id,
                ADF_JUMP_ROLE_NAME,
            ),
            role_session_name,
        )

        jump_role_sts = STS(jump_role_session.client('sts'))
        try:
            session = jump_role_sts.assume_cross_account_role(
                STS._build_role_arn(
                    partition,
                    account_id,
                    privileged_role_name,
                ),
                role_session_name,
            )
            LOGGER.warning(
                "Using the privileged cross-account access role: %s, "
                "as access to this role was granted for account %s",
                privileged_role_name,
                account_id,
            )
            return session
        except botocore.exceptions.ClientError as error:
            if error.response["Error"]["Code"] == ACCESS_DENIED_ERROR_CODE:
                # The access denied error most likely implies that the
                # account is already bootstrapped by ADF. Hence the ADF
                # Bootstrap Update Deployment role should be used instead.
                return jump_role_sts.assume_cross_account_role(
                    STS._build_role_arn(
                        partition,
                        account_id,
                        ADF_BOOTSTRAP_UPDATE_DEPLOYMENT_ROLE_NAME,
                    ),
                    role_session_name,
                )
            raise

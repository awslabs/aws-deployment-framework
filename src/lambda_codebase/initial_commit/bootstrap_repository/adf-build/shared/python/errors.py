# Copyright Amazon.com Inc. or its affiliates.
# SPDX-License-Identifier: MIT-0

"""
A collection of all Error Types used in ADF
"""


class Error(Exception):
    """Base class for exceptions in this module."""


class RetryError(Exception):
    """Retry Error used for Step Functions logic"""


class ParameterNotFoundError(Exception):
    """
    Parameter not found in Parameter Store
    """


class InvalidConfigError(Exception):
    """
    Used for invalid configuration(s) within
    adfconfig.yml and deployment_map.yml
    """


class GenericAccountConfigureError(Exception):
    """
    Generic Account cannot be setup since no base stack is present
    """


class AccountCreationNotFinishedError(Exception):
    """
    When we interact with a Boto3 API call and it fails with the
    SubscriptionRequiredException error code. This implies that the
    account is still being created behind the scenes. To ease troubleshooting
    we raise this Exception class instead. To clarify what is happening.
    """


class RootOUIDError(Exception):
    """
    Raised when an account is moved to the root of the organization
    and a describe call is attempted again the root of the org.
    """


class InvalidTemplateError(Exception):
    """
    Raised when a CloudFormation template fails the Validate Template call
    """


class InvalidDeploymentMapError(Exception):
    """
    Raised when a Deployment Map is invalid
    """


class NoAccountsFoundError(Exception):
    """
    Raised when there are no Accounts found a specific OU defined in the Deployment Map
    """


class InsufficientWaveSizeError(Exception):
    """
    Raised when the defined wave size is less than the calculated minimum actions
    """

# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
A collection of all Error Types used in ADF
"""


class Error(Exception):
    """Base class for exceptions in this module.
    """
    pass


class RetryError(Exception):
    """Retry Error used for Step Functions logic
    """
    pass

class ParameterNotFoundError(Exception):
    """
    Parameter not found in Parameter Store
    """
    pass

class InvalidConfigError(Exception):
    """
     Used for invalid configuration(s) within
     adfconfig.yml and deployment_map.yml
    """

class GenericAccountConfigureError(Exception):
    """
     Generic Account cannot be setup since no base stack is present
    """
    pass

class RootOUIDError(Exception):
    """
     Raised when an account is moved to the root of the organization
     and a describe call is attempted again the root of the org.
    """
    pass

class InvalidTemplateError(Exception):
    """
     Raised when a CloudFormation template fails the Validate Template call
    """
    pass

class InvalidDeploymentMapError(Exception):
    """
     Raised when a Deployment Map is invalid
    """
    pass

class NoAccountsFoundError(Exception):
    """
     Raised when there are no Accounts found a specific OU defined in the Deployment Map
    """
    pass

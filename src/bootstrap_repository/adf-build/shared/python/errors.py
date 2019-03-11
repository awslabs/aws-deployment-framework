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


class InvalidConfigException(Exception):
    """
     Used for invalid configuration(s) within
     adfconfig.yml and deployment_map.yml
    """


class GenericAccountConfigureError(Exception):
    """
     Generic Account cannot be setup since no base stack is present
    """
    pass

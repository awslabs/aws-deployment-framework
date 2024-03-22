# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""Parameter Store module used throughout the ADF
"""

from botocore.config import Config

# ADF imports
from errors import ParameterNotFoundError
from paginator import paginator
from logger import configure_logger

LOGGER = configure_logger(__name__)
PARAMETER_DESCRIPTION = 'DO NOT EDIT - Used by The AWS Deployment Framework'
PARAMETER_PREFIX = '/adf'
SSM_CONFIG = Config(
    retries={
        "max_attempts": 10,
    },
)


class ParameterStore:
    """Class used for modeling Parameters
    """

    def __init__(self, region, role):
        self.client = role.client('ssm', region_name=region, config=SSM_CONFIG)

    def put_parameter(self, name, value, tier='Standard'):
        """Puts a Parameter into Parameter Store
        """
        try:
            current_value = self.fetch_parameter(name)
            assert current_value == value
            LOGGER.debug(
                'No need to update parameter %s/%s with value %s since they '
                'are the same',
                PARAMETER_PREFIX,
                name,
                value,
            )
        except (ParameterNotFoundError, AssertionError):
            LOGGER.debug(
                'Putting SSM Parameter %s/%s with value %s',
                PARAMETER_PREFIX,
                name,
                value,
            )
            self.client.put_parameter(
                Name=f"{PARAMETER_PREFIX}/{name}",
                Description=PARAMETER_DESCRIPTION,
                Value=value,
                Type='String',
                Overwrite=True,
                Tier=tier
            )

    def delete_parameter(self, name):
        try:
            LOGGER.debug('Deleting Parameter %s', name)
            self.client.delete_parameter(
                Name=f"{PARAMETER_PREFIX}/{name}",
            )
        except self.client.exceptions.ParameterNotFound:
            LOGGER.debug(
                'Attempted to delete Parameter %s/%s but it was not found',
                PARAMETER_PREFIX,
                name,
            )

    def fetch_parameters_by_path(self, path):
        """Gets a Parameter(s) by Path from Parameter Store (Recursively)
        """
        try:
            LOGGER.debug(
                'Fetching Parameters from path %s/%s',
                PARAMETER_PREFIX,
                path,
            )
            return paginator(
                self.client.get_parameters_by_path,
                Path=f"{PARAMETER_PREFIX}/{path}",
                Recursive=True,
                WithDecryption=False
            )
        except self.client.exceptions.ParameterNotFound as error:
            raise ParameterNotFoundError(
                f'Parameter Path {PARAMETER_PREFIX}/{path} Not Found',
            ) from error

    def fetch_parameter(self, name, with_decryption=False, adf_only=True):
        """Gets a Parameter from Parameter Store (Returns the Value)
        """
        try:
            param_prefix = PARAMETER_PREFIX if adf_only else '/'
            prefix_seperator = '' if name.startswith('/') else '/'
            param_name = f"{param_prefix}{prefix_seperator}{name}"
            LOGGER.debug(
                'Fetching Parameter %s',
                param_name,
            )
            response = self.client.get_parameter(
                Name=param_name,
                WithDecryption=with_decryption
            )
            return response['Parameter']['Value']
        except self.client.exceptions.ParameterNotFound as error:
            raise ParameterNotFoundError(
                f'Parameter {param_name} Not Found',
            ) from error

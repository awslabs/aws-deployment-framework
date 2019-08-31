# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""Parameter Store module used throughout the ADF
"""

from botocore.config import Config
from errors import ParameterNotFoundError
from paginator import paginator
from logger import configure_logger

LOGGER = configure_logger(__name__)
PARAMETER_DESCRIPTION = 'DO NOT EDIT - Used by The AWS Deployment Framework'
SSM_CONFIG = Config(
    retries=dict(
        max_attempts=10
    )
)

class ParameterStore:
    """Class used for modeling Parameters
    """

    def __init__(self, region, role):
        self.client = role.client('ssm', region_name=region, config=SSM_CONFIG)

    def put_parameter(self, name, value):
        """Puts a Parameter into Parameter Store
        """
        try:
            current_value = self.fetch_parameter(name)
            assert current_value == value
            LOGGER.debug('No need to update parameter %s with value %s since they are the same', name, value)
        except (ParameterNotFoundError, AssertionError):
            LOGGER.debug('Putting SSM Parameter %s with value %s', name, value)
            self.client.put_parameter(
                Name=name,
                Description=PARAMETER_DESCRIPTION,
                Value=value,
                Type='String',
                Overwrite=True
            )

    def delete_parameter(self, name):
        try:
            LOGGER.debug('Deleting Parameter %s', name)
            return self.client.delete_parameter(
                Name=name
            )
        except self.client.exceptions.ParameterNotFound:
            LOGGER.debug('Attempted to delete Parameter %s but it was not found', name)
            pass

    def fetch_parameters_by_path(self, path):
        """Gets a Parameter(s) by Path from Parameter Store (Recursively)
        """
        try:
            LOGGER.debug('Fetching Parameters from path %s', path)
            return paginator(self.client.get_parameters_by_path,
                             Path=path,
                             Recursive=True,
                             WithDecryption=False
                            )
        except self.client.exceptions.ParameterNotFound:
            raise ParameterNotFoundError(
                'Parameter Path {0} Not Found'.format(path)
            )


    def fetch_parameter(self, name, with_decryption=False):
        """Gets a Parameter from Parameter Store (Returns the Value)
        """
        try:
            LOGGER.debug('Fetching Parameter %s', name)
            response = self.client.get_parameter(
                Name=name,
                WithDecryption=with_decryption
            )
            return response['Parameter']['Value']
        except self.client.exceptions.ParameterNotFound:
            raise ParameterNotFoundError(
                'Parameter {0} Not Found'.format(name)
            )

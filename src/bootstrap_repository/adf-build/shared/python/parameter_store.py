# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""Parameter Store module used throughout the ADF
"""

from errors import ParameterNotFoundError
from paginator import paginator

class ParameterStore:
    """Class used for modeling Parameters
    """

    def __init__(self, region, role):
        self.client = role.client('ssm', region_name=region)

    def put_parameter(self, name, value):
        """Puts a Parameter into Parameter Store
        """
        return self.client.put_parameter(
            Name=name,
            Description='DO NOT EDIT - Used by The AWS Deployment Framework',
            Value=value,
            Type='String',
            Overwrite=True)

    def delete_parameter(self, name):
        return self.client.delete_parameter(
            Name=name
        )

    def fetch_parameters_by_path(self, path):
        """Gets a Parameter(s) by Path from Parameter Store (Recursively)
        """
        try:
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
            response = self.client.get_parameter(
                Name=name,
                WithDecryption=with_decryption
            )
            return response['Parameter']['Value']
        except self.client.exceptions.ParameterNotFound:
            raise ParameterNotFoundError(
                'Parameter {0} Not Found'.format(name)
            )

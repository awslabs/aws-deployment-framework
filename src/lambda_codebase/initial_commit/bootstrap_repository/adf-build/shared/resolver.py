# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
This file is pulled into CodeBuild containers
and used to resolve values from Parameter Store and CloudFormation
"""
import os
import boto3

from botocore.exceptions import ClientError
from s3 import S3
from parameter_store import ParameterStore
from partition import get_partition
from cloudformation import CloudFormation
from cache import Cache
from errors import ParameterNotFoundError
from sts import STS
from logger import configure_logger

LOGGER = configure_logger(__name__)
DEFAULT_REGION = os.environ["AWS_REGION"]
S3_BUCKET_NAME = os.environ["S3_BUCKET_NAME"]

class Resolver:
    def __init__(self, parameter_store, stage_parameters, comparison_parameters):
        self.parameter_store = parameter_store
        self.stage_parameters = stage_parameters
        self.comparison_parameters = comparison_parameters
        self.sts = STS()
        self.cache = Cache()

    @staticmethod
    def _is_optional(value):
        return value.endswith('?')

    def fetch_stack_output(self, value, key, optional=False): # pylint: disable=too-many-statements
        partition = get_partition(DEFAULT_REGION)
        try:
            [_, account_id, region, stack_name, output_key] = str(value).split(':')
        except ValueError as error:
            raise ValueError(
                f"{value} is not a valid import string. Syntax should be "
                "import:account_id:region:stack_name:output_key"
            ) from error
        if Resolver._is_optional(output_key):
            LOGGER.info("Parameter %s is considered optional", output_key)
            optional = True
        output_key = output_key[:-1] if optional else output_key
        try:
            role = self.sts.assume_cross_account_role(
                f'arn:{partition}:iam::{account_id}:role/adf-readonly-automation-role',
                'importer'
            )
            cloudformation = CloudFormation(
                region=region,
                deployment_account_region=os.environ["AWS_REGION"],
                role=role,
                stack_name=stack_name,
                account_id=account_id
            )
            stack_output = self.cache.check(value) or cloudformation.get_stack_output(output_key)
            if stack_output:
                LOGGER.info("Stack output value is %s", stack_output)
                self.cache.add(value, stack_output)
        except ClientError:
            if not optional:
                raise
            stack_output = ""
        try:
            parent_key = list(Resolver.determine_parent_key(self.comparison_parameters, key))[0]
            if optional:
                self.stage_parameters[parent_key][key] = stack_output
            else:
                if not stack_output:
                    raise Exception(
                        f"No Stack Output found on {account_id} in {region} "
                        f"with stack name {stack_name} and "
                        f"output key {output_key}"
                    )
                self.stage_parameters[parent_key][key] = stack_output
        except IndexError as error:
            if stack_output:
                if self.stage_parameters.get(key):
                    self.stage_parameters[key] = stack_output
            else:
                raise Exception(
                    "Could not determine the structure of the file in order "
                    "to import from CloudFormation",
                ) from error
        return True

    def upload(self, value, key, file_name):
        if not any(item in value for item in S3.supported_path_styles()):
            raise Exception(
                'When uploading to S3 you need to specify a path style'
                'to use for the returned value to be used. '
                f'Supported path styles include: {S3.supported_path_styles()}'
            ) from None
        if str(value).count(':') > 2:
            [_, region, style, value] = value.split(':')
        else:
            [_, style, value] = value.split(':')
            region = DEFAULT_REGION
        bucket_name = self.parameter_store.fetch_parameter(
            f'/cross_region/s3_regional_bucket/{region}'
        )
        client = S3(region, bucket_name)
        try:
            parent_key = list(Resolver.determine_parent_key(self.comparison_parameters, key))[0]
        except IndexError:
            if self.stage_parameters.get(key):
                self.stage_parameters[key] = client.put_object(
                    f"adf-upload/{value}/{file_name}".format(value, file_name),
                    str(value),
                    style,
                    True  # pre-check
                )
            return True
        self.stage_parameters[parent_key][key] = client.put_object(
            f"adf-upload/{value}/{file_name}",
            str(value),
            style,
            True  # pre-check
        )
        return True

    @staticmethod
    def determine_parent_key(d, target_key, parent_key=None):
        for key, value in d.items():
            if key == target_key:
                yield parent_key
            if isinstance(value, dict):
                for result in Resolver.determine_parent_key(value, target_key, key):
                    yield result

    def fetch_parameter_store_value(self, value, key, optional=False): # pylint: disable=too-many-statements
        if self._is_optional(value):
            LOGGER.info("Parameter %s is considered optional", value)
            optional = True
        if str(value).count(':') > 1:
            [_, region, value] = value.split(':')
        else:
            [_, value] = value.split(':')
            region = DEFAULT_REGION
        value = value[:-1] if optional else value
        client = ParameterStore(region, boto3)
        try:
            parameter = self.cache.check(f'{region}/{value}') or client.fetch_parameter(value)
        except ParameterNotFoundError:
            if optional:
                LOGGER.info("Parameter %s not found, returning empty string", value)
                parameter = ""
            else:
                raise
        try:
            parent_key = list(Resolver.determine_parent_key(self.comparison_parameters, key))[0]
            if parameter:
                self.cache.add(f'{region}/{value}', parameter)
                self.stage_parameters[parent_key][key] = parameter
        except IndexError as error:
            if parameter:
                if self.stage_parameters.get(key):
                    self.stage_parameters[key] = parameter
            else:
                LOGGER.error("Parameter was not found, unable to fetch it from parameter store")
                raise Exception("Parameter was not found, unable to fetch it from parameter store") from error
        return True

    def update(self, key):
        for k, _ in self.comparison_parameters.items():
            if not self.stage_parameters.get(k) and not self.stage_parameters.get(k, {}).get(key):
                self.stage_parameters[k] = self.comparison_parameters[k]
            if key not in self.stage_parameters[k] and self.comparison_parameters.get(k, {}).get(key):
                self.stage_parameters[k][key] = self.comparison_parameters[k][key]

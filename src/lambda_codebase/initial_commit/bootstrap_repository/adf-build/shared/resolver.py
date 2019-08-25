# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""This file is pulled into CodeBuild containers
   and used to resolve values from Parameter Store and CloudFormation
"""
import os
import boto3

from botocore.exceptions import ClientError
from s3 import S3
from parameter_store import ParameterStore
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
        try:
            [_, account_id, region, stack_name, export] = str(value).split(':')
        except ValueError:
            raise ValueError(
                "{0} is not a valid import string."
                "syntax should be import:account_id:region:stack_name:export_key".format(str(value))
            )
        if Resolver._is_optional(export):
            LOGGER.info("Parameter %s is considered optional", export)
            optional = True
        export = export[:-1] if optional else export
        try:
            role = self.sts.assume_cross_account_role(
                'arn:aws:iam::{0}:role/{1}'.format(
                    account_id,
                    'adf-cloudformation-deployment-role'),
                'importer'
            )
            cloudformation = CloudFormation(
                region=region,
                deployment_account_region=os.environ["AWS_REGION"],
                role=role,
                stack_name=stack_name,
                account_id=account_id
            )
            stack_output = self.cache.check(value) or cloudformation.get_stack_output(export)
            if stack_output:
                LOGGER.info("Stack output value is %s", stack_output)
                self.cache.add(value, stack_output)
        except ClientError:
            if not optional:
                raise
            stack_output = ""
            pass
        try:
            parent_key = list(Resolver.determine_parent_key(self.comparison_parameters, key))[0]
            if optional:
                self.stage_parameters[parent_key][key] = stack_output
            else:
                if not stack_output:
                    raise Exception("No Stack Output found on %s in %s with stack name %s and output key %s" % account_id, region, stack_name, export)
                self.stage_parameters[parent_key][key] = stack_output
        except IndexError:
            if stack_output:
                if self.stage_parameters.get(key):
                    self.stage_parameters[key] = stack_output
            else:
                raise Exception("Could not determine the structure of the file in order to import from CloudFormation")
        return True

    def upload(self, value, key, file_name):
        if not any(item in value for item in ['path', 'virtual-hosted']):
            raise Exception(
                'When uploading to S3 you need to specify a '
                'pathing style for the response either path or virtual-hosted, '
                'read more: https://docs.aws.amazon.com/AmazonS3/latest/dev/VirtualHosting.html'
            )
        if str(value).count(':') > 2:
            [_, region, style, value] = value.split(':')
        else:
            [_, style, value] = value.split(':')
            region = DEFAULT_REGION
        bucket_name = self.parameter_store.fetch_parameter(
            '/cross_region/s3_regional_bucket/{0}'.format(region)
        )
        client = S3(region, bucket_name)
        LOGGER.info("Uploading %s as %s to S3 Bucket %s in %s", value, file_name, bucket_name, region)
        try:
            parent_key = list(Resolver.determine_parent_key(self.comparison_parameters, key))[0]
        except IndexError:
            if self.stage_parameters.get(key):
                self.stage_parameters[key] = client.put_object(
                    "adf-upload/{0}/{1}".format(value, file_name),
                    "{0}".format(value),
                    style
                )
            return True
        self.stage_parameters[parent_key][key] = client.put_object(
            "adf-upload/{0}/{1}".format(value, file_name),
            "{0}".format(value),
            style
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
            parameter = self.cache.check('{0}/{1}'.format(region, value)) or client.fetch_parameter(value)
        except ParameterNotFoundError:
            if optional:
                LOGGER.info("Parameter %s not found, returning empty string", value)
                parameter = ""
            else:
                raise
        try:
            parent_key = list(Resolver.determine_parent_key(self.comparison_parameters, key))[0]
            if parameter:
                self.cache.add('{0}/{1}'.format(region, value), parameter)
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

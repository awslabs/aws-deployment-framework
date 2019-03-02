# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""CloudFormation module used throughout the ADF
"""

import re

from logger import configure_logger
from paginator import paginator


LOGGER = configure_logger(__name__)


class StackProperties:
    clean_stack_status = [
        'CREATE_FAILED',
        'CREATE_COMPLETE',
        'ROLLBACK_FAILED',
        'ROLLBACK_COMPLETE',
        'DELETE_FAILED',
        'UPDATE_IN_PROGRESS',
        'UPDATE_COMPLETE_CLEANUP_IN_PROGRESS',
        'UPDATE_COMPLETE',
        'UPDATE_ROLLBACK_IN_PROGRESS',
        'UPDATE_ROLLBACK_FAILED',
        'UPDATE_ROLLBACK_COMPLETE_CLEANUP_IN_PROGRESS',
        'UPDATE_ROLLBACK_COMPLETE',
        'REVIEW_IN_PROGRESS'
    ]

    def __init__(
            self,
            region,
            deployment_account_region,
            stack_name,
            s3_key_path=None,
            s3=None,
            file_path=''):
        self.region = region
        self.deployment_account_region = deployment_account_region
        self.s3_key_path = s3_key_path
        self.ou_name = self.s3_key_path.split(
            '/')[-1] if self.s3_key_path else None
        self.file_path = file_path
        self.s3 = s3
        self.stack_name = stack_name or self._get_stack_name()

    def _get_geo_prefix(self):
        return 'global' if self.region == self.deployment_account_region else 'regional'

    def _create_template_path(self, object_type, path):
        if object_type == 'template':
            return '{0}/{1}.yml'.format(
                path,
                self._get_geo_prefix()
            )
        return '{0}/{1}-params.json'.format(
            path,
            self._get_geo_prefix()
        )

    def get_cfn_resource(self, resource_type):
        try:
            _path = self._create_template_path(resource_type, self.file_path)
            with open(_path, encoding='utf-8') as _data:
                return _data.read()
        except FileNotFoundError:
            return self.s3.s3_stream_object(
                self._create_template_path(resource_type, self.s3_key_path)
            )

    def _get_stack_name(self):
        return 'adf-{0}-base-{1}'.format(
            self._get_geo_prefix(),
            self.ou_name
        )


class CloudFormation(StackProperties):
    def __init__(
            self,
            region,
            deployment_account_region,
            role,
            wait=False,
            stack_name=None,
            s3=None,
            s3_key_path=None,
            file_path=None,
            parameters=None,
    ):
        self.client = role.client('cloudformation', region_name=region)
        self.wait = wait
        self.parameters = parameters
        StackProperties.__init__(
            self,
            region=region,
            deployment_account_region=deployment_account_region,
            stack_name=stack_name,
            s3=s3,
            s3_key_path=s3_key_path,
            file_path=file_path
        )

    def _validate_template(self, template_body):
        return self.client.validate_template(TemplateBody=template_body)

    def _wait_stack(self, waiter_type):
        waiter = self.client.get_waiter(waiter_type)

        LOGGER.info(
            'Waiting for CloudFormation stack: %s in %s to reach %s',
            self.stack_name,
            self.region,
            waiter_type
        )

        waiter.wait(
            StackName=self.stack_name,
            WaiterConfig={
                'Delay': 10,
                'MaxAttempts': 45
            }
        )

    def _wait_change_set(self):
        waiter = self.client.get_waiter('change_set_create_complete')

        LOGGER.info(
            'Determine CloudFormation Change Set: %s in %s',
            self.stack_name, self.region)

        waiter.wait(
            StackName=self.stack_name,
            ChangeSetName=self.stack_name,
            WaiterConfig={
                'Delay': 10,
                'MaxAttempts': 20
            }
        )

    def _get_waiter_type(self):
        return 'stack_update_complete' if self._get_change_set_type(
        ) == 'UPDATE' else 'stack_create_complete'

    def _get_change_set_type(self):
        return 'UPDATE' if self.get_stack_status() else 'CREATE'

    def _describe_change_set(self):
        try:
            return self.client.describe_change_set(
                ChangeSetName=self.stack_name,
                StackName=self.stack_name
            )
        except BaseException:
            return False

    def _create_change_set(self):
        """Creates a Cloudformation change set from a template
        """
        template = self.get_cfn_resource('template')
        if not template:
            return None
        self._validate_template(template)
        try:
            self.client.create_change_set(
                StackName=self.stack_name,
                TemplateBody=template,
                Parameters=self.parameters if self.parameters is not None else self.get_cfn_resource('parameters'),
                Capabilities=[
                    'CAPABILITY_NAMED_IAM',
                ],
                ChangeSetName=self.stack_name,
                ChangeSetType=self._get_change_set_type())

            self._wait_change_set()
            return True
        except BaseException as error:
            change_set = self._describe_change_set()
            if change_set:
                if "The submitted information didn't contain changes." in change_set.get(
                        'StatusReason'):
                    LOGGER.info(
                        "The submitted information does not contain changes.")
            else:
                self._delete_change_set()
                raise error

            self._delete_change_set()
            return None

    def _delete_change_set(self):
        try:
            return self.client.delete_change_set(
                ChangeSetName=self.stack_name,
                StackName=self.stack_name
            )
        except BaseException:
            pass

    def _execute_change_set(self, waiter):
        LOGGER.info(
            'Executing Cloudformation Change Set with name: %s',
            self.stack_name)

        self.client.execute_change_set(
            ChangeSetName=self.stack_name,
            StackName=self.stack_name
        )
        if self.wait:
            self._wait_stack(waiter)

    def create_stack(self):
        waiter = self._get_waiter_type()
        create_change_set = self._create_change_set()
        if create_change_set:
            self._execute_change_set(waiter)

    def get_stack_regional_outputs(self):
        return {
            "kms_arn": self._get_stack_output("DeploymentFrameworkRegionalKMSKey"),
            "s3_regional_bucket": self._get_stack_output("DeploymentFrameworkRegionalS3Bucket")
        }

    def delete_all_base_stacks(self):
        for stack in paginator(self.client.list_stacks):
            if bool(
                    re.search(
                        'adf-(global|regional)-base',
                        stack.get('StackName'))):
                if stack.get(
                        'StackStatus') in StackProperties.clean_stack_status:
                    LOGGER.warning(
                        'Removing Stack: %s',
                        stack.get('StackName'))
                    self.delete_stack(stack.get('StackName'))

    def _get_stack_output(self, value):
        try:
            response = self.client.describe_stacks(
                StackName=self.stack_name
            )
            return [item.get('OutputValue') for item in response.get('Stacks')
                    [0].get('Outputs') if item.get('OutputKey') == value][0]
        except BaseException:
            return None  # Return None if describe stack call fails

    def get_stack_status(self):
        try:
            stack = self.client.describe_stacks(
                StackName=self.stack_name
            )
            return stack['Stacks'][0]['StackStatus']
        except BaseException:
            return None  # Return None if the stack does not exist

    def delete_stack(self, stack_name):
        self.stack_name = stack_name
        self.client.delete_stack(
            StackName=self.stack_name
        )
        if self.wait:
            self._wait_stack('stack_delete_complete')

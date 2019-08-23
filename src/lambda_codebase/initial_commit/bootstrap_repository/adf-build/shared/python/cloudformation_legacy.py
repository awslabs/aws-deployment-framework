# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""CloudFormation module used throughout the ADF
"""

import os

from botocore.exceptions import WaiterError, ClientError
from errors import InvalidTemplateError, GenericAccountConfigureError
from logger import configure_logger
from cloudformation import StackProperties

LOGGER = configure_logger(__name__)
STACK_TERMINATION_PROTECTION = os.environ.get('TERMINATION_PROTECTION', False)

class CloudFormationLegacy(StackProperties):
    def __init__(
            self,
            region,
            deployment_account_region,
            role,
            template_url=None,
            wait=False,
            stack_name=None,
            s3=None,
            s3_key_path=None,
            parameters=None,
            account_id=None, # Used for logging visibility
    ):
        self.client = role.client('cloudformation', region_name=region)
        self.wait = wait
        self.parameters = parameters
        self.account_id = account_id
        self.template_url = template_url
        StackProperties.__init__(
            self,
            region=region,
            deployment_account_region=deployment_account_region,
            stack_name=stack_name,
            s3=s3,
            s3_key_path=s3_key_path
        )

    def validate_template(self):
        try:
            return self.client.validate_template(TemplateURL=self.template_url)
        except ClientError as error:
            raise InvalidTemplateError("{0}: {1}".format(self.template_url, error)) from None

    def _update_stack_termination_protection(self):
        try:
            return self.client.update_termination_protection(
                EnableTerminationProtection=STACK_TERMINATION_PROTECTION == "True",
                StackName=self.stack_name
            )
        except ClientError:
            LOGGER.info(
                '%s - Attempted to Update Stack Termination Protection: %s, It is not required.',
                self.account_id, self.stack_name, )
            pass

    def create_stack(self):
        try:
            params = {
                'StackName': self.stack_name,
                'TemplateURL': self.template_url,
                'Parameters': self.parameters,
            }
            if self._stack_exists(self.stack_name):
                LOGGER.info('Updating %s', self.stack_name)
                self.client.update_stack(**params)
                waiter = self.client.get_waiter('stack_update_complete')
            else:
                LOGGER.info('Creating %s', self.stack_name)
                self.client.create_stack(**params)
                waiter = self.client.get_waiter('stack_create_complete')
            LOGGER.info("...waiting for stack to be ready...")
            waiter.wait(StackName=self.stack_name)
        except ClientError as ex:
            error_message = ex.response['Error']['Message']
            if error_message == 'No updates are to be performed.':
                print("No changes")
            else:
                raise
        self._update_stack_termination_protection()

    def _stack_exists(self, stack_name):
        stacks = self.client.list_stacks()['StackSummaries']
        for stack in stacks:
            if stack['StackStatus'] == 'DELETE_COMPLETE':
                continue
            if stack_name == stack['StackName']:
                return True
        return False

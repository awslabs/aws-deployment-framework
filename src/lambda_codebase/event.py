# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
Module to define the structure of the event
used in Step Functions when accounts are moved
into Organizational Units
"""

import ast
import os
from errors import ParameterNotFoundError, RootOUIDError

DEPLOYMENT_ACCOUNT_OU_NAME = 'deployment'
DEPLOYMENT_ACCOUNT_S3_BUCKET = os.environ["DEPLOYMENT_ACCOUNT_BUCKET"]
ADF_VERSION = os.environ["ADF_VERSION"]
ADF_LOG_LEVEL = os.environ["ADF_LOG_LEVEL"]

class Event:
    """
    Class for structuring the Event in Step Functions
    """
    def __init__(self, event, parameter_store, organizations, account_id):
        self.parameter_store = parameter_store
        self.config = ast.literal_eval(
            parameter_store.fetch_parameter(
                'config'
            )
        )
        self.account_id = account_id
        self.organizations = organizations
        self.protected_ou_list = self.config.get('protected', [])
        self.is_deployment_account = 0
        self.deployment_account_id = None
        self.destination_ou_name = None
        self.source_ou_id = event.get(
            'detail').get(
                'requestParameters').get('sourceParentId')
        self.main_notification_endpoint = self.config.get(
            'main-notification-endpoint').pop().get('target')
        self.notification_type = 'lambda' if '@' not in self.main_notification_endpoint else 'email'
        self.moved_to_root = 1 if event.get(
            'detail').get(
                'requestParameters').get(
                    'destinationParentId').startswith('r-') else 0
        self.destination_ou_id = event.get(
            'detail').get(
                'requestParameters').get('destinationParentId')
        self.moved_to_protected = 1 if self.destination_ou_id in self.protected_ou_list else 0
        self.regions = ast.literal_eval(
            parameter_store.fetch_parameter('target_regions')
        ) or []
        self.deployment_account_region = parameter_store.fetch_parameter(
            'deployment_account_region')
        self.cross_account_access_role = parameter_store.fetch_parameter(
            'cross_account_access_role')
        self.set_destination_ou_name()


    def _determine_if_deployment_account(self):
        """
        Sets property based on if the account that has been moved
        is the deployment account also attempts to fetch the Deployment Account Id
        value from parameter store if it doesn't exist then the
        account requesting must be the deployment account itself.
        """
        self.is_deployment_account = 1 if self.destination_ou_name == DEPLOYMENT_ACCOUNT_OU_NAME else 0
        try:
            self.deployment_account_id = self.parameter_store.fetch_parameter('deployment_account_id')
        except ParameterNotFoundError:
            self.deployment_account_id = self.account_id

    def set_destination_ou_name(self):
        """
        Sets the destination_ou name property with the name of the OU
        That the account was moved into, afterwards determines if that name
        was 'deployment'.
        """
        try:
            self.destination_ou_name = self.organizations.describe_ou_name(
                self.destination_ou_id
            )
        except RootOUIDError:
            self.destination_ou_name = "ROOT"
        finally:
            self._determine_if_deployment_account()

    def create_output_object(self, account_path):
        """
        Creates the output object to be passed to the next step
        of the Step Function
        """
        organization_information = self.organizations.get_organization_info()

        return {
            'account_id': self.account_id,
            'cross_account_access_role': self.cross_account_access_role,
            'deployment_account_id': self.deployment_account_id,
            'regions': self.regions,
            'deployment_account_region': self.deployment_account_region,
            'moved_to_root': self.moved_to_root,
            'moved_to_protected': self.moved_to_protected,
            'is_deployment_account': self.is_deployment_account,
            'ou_name': self.destination_ou_name,
            'full_path': "ROOT" if self.moved_to_root else account_path,
            'destination_ou_id': self.destination_ou_id,
            'source_ou_id': self.source_ou_id,
            'deployment_account_parameters' : {
                'organization_id': organization_information.get(
                    "organization_id"
                ),
                'master_account_id': organization_information.get(
                    "organization_master_account_id"
                ),
                'notification_endpoint': self.main_notification_endpoint,
                'notification_type': self.notification_type,
                'cross_account_access_role': self.cross_account_access_role,
                'deployment_account_bucket': DEPLOYMENT_ACCOUNT_S3_BUCKET,
                'adf_version': ADF_VERSION,
                'adf_log_level': ADF_LOG_LEVEL
            }
        }

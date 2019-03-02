# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
Module to define the structure of the event
used in Step Functions when accounts are moved
into Organizational Units
"""

import ast
import os

DEPLOYMENT_ACCOUNT_OU_NAME = 'deployment'
DEPLOYMENT_ACCOUNT_S3_BUCKET = os.environ.get("DEPLOYMENT_ACCOUNT_BUCKET")


class Event:
    def __init__(self, event, parameter_store, organizations, account_id):
        self.config = ast.literal_eval('{0}'.format(
            parameter_store.fetch_parameter(
                'config'
            )
        ))
        self.account_id = account_id
        self.organizations = organizations
        self.protected_ou_list = self.config.get('protected', [])
        self.is_deployment_account = 0
        self.main_notification_endpoint = self.config.get(
            'main-notification-endpoint', None
        ).pop().get('target')
        self.moved_to_root = 1 if event.get(
            'detail').get(
                'requestParameters').get(
                    'destinationParentId').startswith('r-') else 0
        self.destination_ou_id = event.get(
            'detail').get(
                'requestParameters').get('destinationParentId')
        self.moved_to_protected = 1 if self.destination_ou_id in self.protected_ou_list else 0
        self.deployment_account_id = self.account_id if self.is_deployment_account else parameter_store.fetch_parameter(
            'deployment_account_id')
        self.regions = ast.literal_eval(
            parameter_store.fetch_parameter('target_regions')
        )
        self.deployment_account_region = parameter_store.fetch_parameter(
            'deployment_account_region')
        self.cross_account_access_role = parameter_store.fetch_parameter(
            'cross_account_access_role')
        self.destination_ou_name = None
        self._ensure_deployment_order()

    def _determine_if_deployment_account(self):
        self.is_deployment_account = 1 if self.destination_ou_name == DEPLOYMENT_ACCOUNT_OU_NAME else 0

    def set_destination_ou_name(self):
        self.destination_ou_name = self.organizations.describe_ou_name(
            self.destination_ou_id
        )
        self._determine_if_deployment_account()

    def create_deployment_account_parameters(self):
        organization_information = self.organizations.get_organization_info()
        return {
            'deployment_account_id': self.account_id,
            'cross_account_access_role': self.cross_account_access_role,
            'organization_id': organization_information.get(
                "organization_id"
            ),
            'master_account_id': organization_information.get(
                "organization_master_account_id"
            ),
            'notification_endpoint': self.main_notification_endpoint,
            'deployment_account_bucket': DEPLOYMENT_ACCOUNT_S3_BUCKET
        }

    def create_output_object(self, cache):
        return {
            'account_id': self.account_id,
            'cross_account_iam_role': self.cross_account_access_role,
            'deployment_account_id': self.deployment_account_id,
            'regions': self.regions,
            'deployment_account_region': self.deployment_account_region,
            'moved_to_root': self.moved_to_root,
            'moved_to_protected': self.moved_to_protected,
            'is_deployment_account': self.is_deployment_account,
            'ou_name': self.destination_ou_name,
            'full_path': "ROOT" if self.moved_to_root else self.organizations.build_account_path(
                self.destination_ou_id,
                [],  # Initial empty array to hold OU Path
                cache
            )
        }

    def _ensure_deployment_order(self):
        """
        Ensure that the deployment account region
        occurs first for deployments if its also a target
        """
        if self.deployment_account_region in self.regions:
            regions = self.regions
            regions.pop(regions.index(self.deployment_account_region))
            regions.insert(0, self.deployment_account_region)
            self.regions = regions

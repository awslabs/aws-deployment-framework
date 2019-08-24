# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""Config module used as part of bootstrap_repository
Relates to working with the adfconfig.yml file
"""

import os
import yaml
import boto3

from errors import InvalidConfigError
from logger import configure_logger
from parameter_store import ParameterStore

ADF_VERSION = os.environ["ADF_VERSION"]
LOGGER = configure_logger(__name__)


class Config:
    """Class used for modeling dfconfig and its properties
    """

    def __init__(self, parameter_store=None, config_path=None):
        self.parameters_client = parameter_store or ParameterStore(
            os.environ["AWS_REGION"],
            boto3
        )
        self.config_path = config_path or './adfconfig.yml'
        self.organization_id = os.environ["ORGANIZATION_ID"]
        self.client_deployment_region = None
        self.notification_type = None
        self.notification_endpoint = None
        self.config_contents = None
        self.config = None
        self.deployment_account_region = None
        self.notification_channel = None
        self.protected = None
        self.target_regions = []
        self.cross_account_access_role = None
        self._load_config_file()

    def store_config(self):
        self._store_config()
        self._store_cross_region_config()

    def _validate(self):
        """
        Validates the adfconfig.yml file
        """
        if None in (
                self.cross_account_access_role,
                self.config,
                self.deployment_account_region,
                self.organization_id,
                self.target_regions,
                self.config.get('moves'),
                self.config.get('main-notification-endpoint')
        ):
            raise InvalidConfigError(
                'adfconfig.yml is missing required properties. '
                'Please see the documentation.'
            )

        try:
            if self.config.get('scp'):
                assert self.config.get('scp').get('keep-default-scp') in ['enabled', 'disabled']
        except AssertionError:
            raise InvalidConfigError(
                'Configuration settings for organizations should be either enabled or disabled'
            )

        if isinstance(self.deployment_account_region, list):
            if len(self.deployment_account_region) > 1:
                raise InvalidConfigError(
                    'ADF currently only supports a single '
                    'Deployment Account region'
                )
            [self.deployment_account_region] = self.deployment_account_region

        if not isinstance(self.target_regions, list):
            self.target_regions = [self.target_regions]

    def _load_config_file(self):
        """
        Loads the adfconfig.yml file and executes _parse_config
        """
        with open(self.config_path) as config:
            self.config_contents = yaml.load(config, Loader=yaml.FullLoader)
            self._parse_config()

    def _parse_config(self):
        """
        Parses the adfconfig.yml file and executes _validate
        """
        regions = self.config_contents.get(
            'regions', {}).get('targets', [])
        self.deployment_account_region = self.config_contents.get(
            'regions', None).get('deployment-account', None)
        self.target_regions = [] if regions[0] is None else regions
        self.cross_account_access_role = self.config_contents.get(
            'roles', None).get('cross-account-access', None)
        self.config = self.config_contents.get('config', None)
        self.protected = self.config.get('protected', [])
        self.notification_type = 'lambda' if self.config.get(
            'main-notification-endpoint')[0].get('type') == 'slack' else 'email'
        self.notification_endpoint = self.config.get(
            'main-notification-endpoint')[0].get('target')
        self.notification_channel = None if self.notification_type == 'email' else self.notification_endpoint

        self._validate()

    def _store_cross_region_config(self):
        """
        Stores cross_account_access_role Parameter
        in Parameter Store on the master account
        in deployment account main region.
        """
        self.client_deployment_region = ParameterStore(
            self.deployment_account_region,
            boto3
        )
        self.client_deployment_region.put_parameter(
            'adf_version',
            ADF_VERSION
        )
        self.client_deployment_region.put_parameter(
            'cross_account_access_role',
            self.cross_account_access_role
        )

    def _store_config(self):
        """
        Stores the required configuration in Parameter Store on
        The master account in us-east-1.
        """
        for key, value in self.__dict__.items():
            if key not in (
                    "client",
                    "client_deployment_region",
                    "parameters_client",
                    "config_contents",
                    "config_path",
                    "notification_endpoint",
                    "notification_type"
            ):
                self.parameters_client.put_parameter(key, str(value))

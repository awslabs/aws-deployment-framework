# Copyright Amazon.com Inc. or its affiliates.
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
AVAILABLE_EXTENSIONS = ["terraform"]


class Config:
    """
    Class used for modeling adfconfig and its properties.
    """
    # pylint: disable=too-many-instance-attributes

    def __init__(self, parameter_store=None, config_path=None):
        self.parameters_client = parameter_store or ParameterStore(
            os.environ["AWS_REGION"], boto3
        )
        self.config_path = config_path or "./adfconfig.yml"
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
        self.extensions = None
        self._load_config_file()

    def sorted_regions(self):
        target_regions_except_deploy = sorted(list(
            set(self.target_regions)
            - set([self.deployment_account_region])
        ))
        return [
            # Make sure we start with the main deployment region
            self.deployment_account_region,
            # Followed by all other target regions configured
            *target_regions_except_deploy,
        ]

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
            self.config.get("moves"),
            self.config.get("main-notification-endpoint"),
        ):
            raise InvalidConfigError(
                "adfconfig.yml is missing required properties. "
                "Please see the documentation."
            ) from None
        if "" in (
            self.cross_account_access_role,
            self.deployment_account_region,
            self.notification_endpoint,
        ):
            raise InvalidConfigError(
                "adfconfig.yml is missing required properties, set as ''. "
                "Please see the documentation."
            ) from None
        if self.notification_type == "email" and "@" not in self.notification_endpoint:
            raise InvalidConfigError(
                "The main-notification-endpoint configured in adfconfig.yml, "
                "is configured as an email, but lacks the '@' character. "
                "Please see the documentation."
            ) from None

        if self.config.get("scp"):
            valid_options = ["enabled", "disabled"]
            if self.config.get("scp").get("keep-default-scp") not in valid_options:
                raise InvalidConfigError(
                    "Configuration settings for organizations should be either "
                    "enabled or disabled"
                ) from None

        if isinstance(self.deployment_account_region, list):
            if len(self.deployment_account_region) > 1:
                raise InvalidConfigError(
                    "ADF currently only supports a single "
                    "Deployment Account region"
                ) from None
            [self.deployment_account_region] = self.deployment_account_region

        if not isinstance(self.target_regions, list):
            self.target_regions = [self.target_regions]

    def _load_config_file(self):
        """
        Checks for an Org Specific adfconfig.yml (adfconfig.{ORG_ID}.yml)
        and uses that if it exists. Otherwise it uses the default adfconfig.yml
        and executes _parse_config
        """
        org_config_path = self.config_path.replace(".yml", f".{self.organization_id}.yml")
        if os.path.exists(org_config_path):
            with open(org_config_path, encoding="utf-8") as org_config_file:
                LOGGER.info("Using organization specific ADF config: %s", org_config_path)
                self.config_contents = yaml.safe_load(org_config_file)
        else:
            LOGGER.info("Using default ADF config: %s", self.config_path)
            with open(self.config_path, encoding="utf-8") as config:
                self.config_contents = yaml.safe_load(config)
        self._parse_config()

    def _parse_config(self):
        """
        Parses the adfconfig.yml file and executes _validate
        """
        regions = self.config_contents.get("regions", {}).get("targets", [])
        self.deployment_account_region = self.config_contents.get("regions", {}).get(
            "deployment-account"
        )
        self.target_regions = [] if regions[0] is None else regions
        self.cross_account_access_role = self.config_contents.get("roles", {}).get(
            "cross-account-access"
        )
        self.config = self.config_contents.get("config")
        self.protected = self.config.get("protected", [])

        # TODO Investigate why this only considers the first notification
        # endpoint. Seems like a bug, it should support multiple.
        main_notification_endpoint = (self.config.get("main-notification-endpoint") or [{}])[0]
        self.notification_type = (
            "lambda" if main_notification_endpoint.get("type") == "slack" else "email"
        )
        self.notification_endpoint = main_notification_endpoint.get("target", "")
        self.notification_channel = (
            None if self.notification_type == "email" else self.notification_endpoint
        )

        self.extensions = self.config_contents.get("extensions", {})
        self._configure_default_extensions_behavior()

        self._validate()

    def _configure_default_extensions_behavior(self):
        for unconfigured_extension in AVAILABLE_EXTENSIONS - self.extensions.keys():
            self.extensions[unconfigured_extension] = {"enabled": False}

    def _store_cross_region_config(self):
        """
        Stores cross_account_access_role Parameter
        in Parameter Store on the management account
        in deployment account main region.
        """
        deployment_account_id = self.parameters_client.fetch_parameter(
            'deployment_account_id',
        )

        self.client_deployment_region = ParameterStore(
            self.deployment_account_region, boto3
        )
        self.client_deployment_region.put_parameter("adf_version", ADF_VERSION)
        self.client_deployment_region.put_parameter(
            "deployment_account_id",
            deployment_account_id,
        )
        self.client_deployment_region.put_parameter(
            "cross_account_access_role",
            self.cross_account_access_role,
        )

    def _store_config(self):
        """
        Stores the required configuration in Parameter Store on
        The management account in us-east-1.
        """
        for key, value in self.__dict__.items():
            if key not in (
                "client",
                "client_deployment_region",
                "parameters_client",
                "config_contents",
                "config_path",
                "notification_endpoint",
                "notification_type",
                "extensions",
            ):
                self.parameters_client.put_parameter(key, str(value))

        for move in self.config.get('moves', []):
            move_param_name = move.get('name', '').replace('-', '_')
            if move_param_name and move.get('action'):
                self.parameters_client.put_parameter(
                    f"moves/{move_param_name}/action",
                    str(move.get('action')),
                )

        for extension, attributes in self.extensions.items():
            for attribute in attributes:
                self.parameters_client.put_parameter(
                    f"extensions/{extension}/{attribute}",
                    str(attributes[attribute]),
                )

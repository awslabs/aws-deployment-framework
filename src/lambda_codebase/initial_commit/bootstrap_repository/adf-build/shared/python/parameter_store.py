# Copyright Amazon.com Inc. or its affiliates.
# SPDX-License-Identifier: MIT-0

"""Parameter Store module used throughout the ADF
"""

from botocore.config import Config

# ADF imports
from cache import Cache
from errors import ParameterNotFoundError
from paginator import paginator
from logger import configure_logger

LOGGER = configure_logger(__name__)
PARAMETER_DESCRIPTION = "DO NOT EDIT - Used by The AWS Deployment Framework"
PARAMETER_PREFIX = "/adf"
SSM_CONFIG = Config(
    retries={
        "max_attempts": 10,
    },
)


class ParameterStore:
    """Class used for modeling Parameters"""

    def __init__(self, region, role, cache=None):
        self.cache = cache or Cache()
        self.client = role.client("ssm", region_name=region, config=SSM_CONFIG)

    def put_parameter(self, name, value, tier="Standard"):
        """Puts a Parameter into Parameter Store"""
        try:
            current_value = self.fetch_parameter(name)
            assert current_value == value
            LOGGER.debug(
                "No need to update parameter %s with value %s since they "
                "are the same",
                ParameterStore._build_param_name(name),
                value,
            )
        except (ParameterNotFoundError, AssertionError):
            param_name = ParameterStore._build_param_name(name)
            LOGGER.debug(
                "Putting SSM Parameter %s with value %s",
                param_name,
                value,
            )
            self.client.put_parameter(
                Name=param_name,
                Description=PARAMETER_DESCRIPTION,
                Value=value,
                Type="String",
                Overwrite=True,
                Tier=tier,
            )
            self.cache.add(param_name, value)

    def delete_parameter(self, name):
        param_name = ParameterStore._build_param_name(name)
        try:
            LOGGER.debug("Deleting Parameter %s", param_name)
            self.cache.remove(param_name)
            self.client.delete_parameter(
                Name=param_name,
            )
        except self.client.exceptions.ParameterNotFound:
            LOGGER.debug(
                "Attempted to delete Parameter %s but it was not found",
                param_name,
            )

    def fetch_parameters_by_path(self, path):
        """Gets a Parameter(s) by Path from Parameter Store (Recursively)"""
        param_path = ParameterStore._build_param_name(path)
        try:
            LOGGER.debug(
                "Fetching Parameters from path %s",
                param_path,
            )
            return paginator(
                self.client.get_parameters_by_path,
                Path=param_path,
                Recursive=True,
                WithDecryption=False,
            )
        except self.client.exceptions.ParameterNotFound as error:
            raise ParameterNotFoundError(
                f"Parameter Path {param_path} Not Found",
            ) from error

    @staticmethod
    def _build_param_name(name, adf_only=True):
        slash_name = name if name.startswith("/") else f"/{name}"
        add_prefix = adf_only and not slash_name.startswith(f"{PARAMETER_PREFIX}/")
        param_prefix = PARAMETER_PREFIX if add_prefix else ""
        return f"{param_prefix}{slash_name}"

    def fetch_parameter(self, name, with_decryption=False, adf_only=True):
        """Gets a Parameter from Parameter Store (Returns the Value)"""
        param_name = ParameterStore._build_param_name(name, adf_only)
        if self.cache.exists(param_name):
            LOGGER.debug("Reading Parameter from Cache: %s", param_name)
            cached_value = self.cache.get(param_name)
            if isinstance(cached_value, ParameterNotFoundError):
                raise cached_value
            return cached_value
        try:
            LOGGER.debug("Fetching Parameter %s", param_name)
            response = self.client.get_parameter(
                Name=param_name, WithDecryption=with_decryption
            )
            fetched_value = response["Parameter"]["Value"]
            self.cache.add(param_name, fetched_value)
            return fetched_value
        except self.client.exceptions.ParameterNotFound as error:
            LOGGER.debug("Parameter %s not found", param_name)
            not_found = ParameterNotFoundError(
                f"Parameter {param_name} Not Found",
            )
            self.cache.add(param_name, not_found)
            raise not_found from error

    def fetch_parameter_accept_not_found(
        self,
        name,
        with_decryption=False,
        adf_only=True,
        default_value=None,
    ):
        """
        Performs the fetch_parameter action, while catching the
        ParameterNotFoundError and returning the configured default_value
        instead if this happens.
        """
        try:
            return self.fetch_parameter(name, with_decryption, adf_only)
        except ParameterNotFoundError:
            LOGGER.debug("Using default instead: %s", default_value)
            return default_value

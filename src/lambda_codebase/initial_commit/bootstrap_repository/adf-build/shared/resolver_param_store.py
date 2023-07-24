# Copyright 2022 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
ResolverParamStore class used to resolve parameter store lookups.
"""
import os
from typing import Tuple
import boto3
from logger import configure_logger
from parameter_store import ParameterStore
from errors import ParameterNotFoundError
from base_resolver import BaseResolver

LOGGER = configure_logger(__name__)
DEFAULT_REGION = os.environ["AWS_REGION"]


class ResolverParamStore(BaseResolver):
    """
    The Parameter Store Resolver is able to resolve the parameter
    as instructed using the 'resolve:' syntax.
    """

    @staticmethod
    def _get_region_and_param_path(lookup_str: str) -> Tuple[str, str]:
        lookup_split = lookup_str.split(':')
        # The last element is the path
        path = lookup_split[-1]
        region = lookup_split[-2] if len(lookup_split) > 2 else DEFAULT_REGION
        return (region, path)

    # pylint: disable=unused-argument
    def resolve(self, lookup_str: str, random_filename: str) -> str:
        """
        Assumes that the lookup_str starts with 'resolve:'.

        This function will perform a lookup in parameter store
        to find the value as requested by the lookup_str.

        Args:
            lookup_str (str): The lookup string that contains the
                `resolve:` lookup path.
            random_filename (str): The random filename, not used in this
                function.

        Returns:
            str: The value as looked up in parameter store.
        """
        optional = self._is_optional(lookup_str)
        if optional:
            LOGGER.info("Parameter %s is considered optional", lookup_str)
            lookup_str = lookup_str[:-1]
        [region, param_path] = self._get_region_and_param_path(lookup_str)
        cache_key = f'{region}/{param_path}'
        if self.cache.exists(cache_key):
            return self.cache.get(cache_key)
        client = ParameterStore(region, boto3)
        try:
            param_value = client.fetch_parameter(param_path)
            if param_value:
                self.cache.add(f'{region}/{param_path}', param_value)
                return param_value
        except ParameterNotFoundError:
            if not optional:
                raise
            LOGGER.info(
                "Parameter %s not found, returning empty string",
                param_path,
            )
        return ""

    # To enable an easy interface that could do lookups
    # whether a specific lookup string is supported or not it
    # should be instance based. Disabling: no-self-use warning
    def supports(self, lookup_str: str) -> bool:
        """
        Check if this resolver supports the lookup_str syntax.

        Args:
            lookup_str (str): The lookup string that might have resolve: or
                another resolver syntax.

        Returns:
            bool: True if this resolver supports the lookup_str syntax.
                In other words, the lookup_str starts with `resolve:`.
                False if not.
        """
        return lookup_str.startswith('resolve:')

# Copyright 2022 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
ResolverUpload class used to upload files to S3.
"""
import os
from typing import Tuple
from base_resolver import BaseResolver
from logger import configure_logger
from parameter_store import ParameterStore
from s3 import S3

LOGGER = configure_logger(__name__)
DEFAULT_REGION = os.environ["AWS_REGION"]


class ResolverUpload(BaseResolver):
    """
    The S3 Upload Resolver is able to resolve `upload:` syntax.
    It will upload the local file to the S3 bucket and resolve the
    path to the object in the requested path syntax.
    """

    def __init__(self, parameter_store: ParameterStore):
        BaseResolver.__init__(self)
        self.parameter_store = parameter_store

    @staticmethod
    def _get_region_style_and_object_key(
        lookup_str: str,
    ) -> Tuple[str, str, str]:
        lookup_split = lookup_str.split(':')
        # The last element is the object_key
        object_key = lookup_split[-1]
        style = lookup_split[-2]
        region = lookup_split[-3] if len(lookup_split) > 3 else DEFAULT_REGION
        return (region, style, object_key)

    def resolve(self, lookup_str: str, random_filename: str) -> str:
        """
        Assumes that the lookup_str starts with 'upload:'.

        This function will perform an upload of the specified file to S3
        and return the path to the object as requested by the lookup_str.

        Args:
            lookup_str (str): The lookup string that contains the
                `upload:` instructions.
            random_filename (str): The random filename, used to upload a
                unique object to the S3 bucket.

        Returns:
            str: The path to the uploaded object in S3.
        """
        if not any(
            item in lookup_str
            for item in S3.supported_path_styles()
        ):
            raise ValueError(
                'When uploading to S3 you need to specify a path style'
                'to use for the returned value to be used. '
                f'Supported path styles include: {S3.supported_path_styles()}'
            ) from None
        if self.cache.exists(lookup_str):
            return self.cache.get(lookup_str)
        (region, style, object_key) = self._get_region_style_and_object_key(
            lookup_str,
        )
        bucket_name = self.parameter_store.fetch_parameter(
            f'cross_region/s3_regional_bucket/{region}'
        )
        s3_client = S3(region, bucket_name)
        resolved_location = s3_client.put_object(
            f"adf-upload/{object_key}/{random_filename}",
            str(object_key),
            style,
            True  # pre-check
        )
        self.cache.add(lookup_str, resolved_location)
        return resolved_location

    # To enable an easy interface that could do lookups
    # whether a specific lookup string is supported or not it
    # should be instance based. Disabling: no-self-use warning
    def supports(self, lookup_str: str) -> bool:
        """
        Check if this resolver supports the lookup_str syntax.

        Args:
            lookup_str (str): The lookup string that might have upload: or
                another resolver syntax.

        Returns:
            bool: True if this resolver supports the lookup_str syntax.
                In other words, the lookup_str starts with `upload:`.
                False if not.
        """
        return lookup_str.startswith('upload:')

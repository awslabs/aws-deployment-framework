# Copyright 2022 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
BaseResolver abstract class used for resolver implementations
to inherit from so they use the same interface
"""
from abc import ABC, abstractmethod
from cache import Cache


class BaseResolver(ABC):
    """
    The abstract BaseResolver class ensures that the interface
    of the methods for resolvers are defined and common code is stored here.
    """

    def __init__(self):
        self.cache = Cache()

    @abstractmethod
    def resolve(self, lookup_str: str, random_filename: str) -> str:
        """
        Assumes that the lookup_str is supported.

        This function will perform the intrinsic function to
        resolve the value as requested.

        Args:
            lookup_str (str): The lookup string that contains the lookup
                syntax.
            random_filename (str): The random filename, used to ensure
                unique uploads when required.

        Returns:
            str: The value as looked up using the intrinsic function.
        """
        pass

    @abstractmethod
    def supports(self, lookup_str: str) -> bool:
        """
        Check if this resolver supports the lookup_str syntax.

        Args:
            lookup_str (str): The lookup string that might have the lookup
                syntax or not.

        Returns:
            bool: True if this resolver supports the lookup_str syntax.
                False if not.
        """
        pass

    @staticmethod
    def _is_optional(value: str) -> bool:
        return value.endswith('?')

# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
This file is pulled into CodeBuild containers
and used to resolve values from Parameter Store and CloudFormation
"""
from typing import Optional
from parameter_store import ParameterStore
from base_resolver import BaseResolver
from resolver_param_store import ResolverParamStore
from resolver_stack_output import ResolverStackOutput
from resolver_upload import ResolverUpload


class Resolver:
    """
    Resolver class responsible for managing the intrinsic
    resolvers that are available.
    """
    def __init__(self, parameter_store: ParameterStore):
        self.resolvers = [
            ResolverParamStore(),
            ResolverStackOutput(),
            ResolverUpload(parameter_store),
        ]

    def _matching_intrinsic_resolver(
        self,
        lookup_str: str
    ) -> Optional[BaseResolver]:
        matches = list(filter(
            lambda resolver: resolver.supports(lookup_str),
            self.resolvers,
        ))
        return None if len(matches) == 0 else matches[0]

    def apply_intrinsic_function_if_any(
        self,
        lookup_value: str,
        file_name: str,
    ) -> str:
        """
        Apply the first intrinsic function that matches if there is one.
        Otherwise return the lookup_value as is.

        Args:
            lookup_value (str): The lookup value that could instruct an
                intrinsic function to lookup the value as specified.
            file_name (str): The random string used to create unique
                file uploads when required.

        Return:
            str: The resolved value using the first matching intrinsic
                resolver if any. Or the lookup_value as passed to the
                function if no intrinsic resolvers support the lookup.
        """
        matching_resolver = self._matching_intrinsic_resolver(lookup_value)
        if matching_resolver is not None:
            return matching_resolver.resolve(
                lookup_value,
                file_name,
            )
        return lookup_value

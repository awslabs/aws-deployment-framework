# Copyright Amazon.com Inc. or its affiliates.
# SPDX-License-Identifier: MIT-0

"""
ResolverStackOutput class used to resolve CloudFormation Stack output lookups.
"""
import os
from botocore.exceptions import ClientError
from logger import configure_logger
from partition import get_partition
from cloudformation import CloudFormation
from sts import STS
from base_resolver import BaseResolver

LOGGER = configure_logger(__name__)
DEFAULT_REGION = os.environ["AWS_REGION"]


class ResolverStackOutput(BaseResolver):
    """
    The CloudFormation Stack Output Resolver is able to resolve `import:`
    syntax. It will perform a lookup in the requested CloudFormation stack
    for the output value of the key as specified in the lookup syntax.
    """

    def __init__(self):
        BaseResolver.__init__(self)
        self.sts = STS()

    def _get_stack(
        self,
        account_id: str,
        region: str,
        stack_name: str,
    ) -> CloudFormation:
        partition = get_partition(DEFAULT_REGION)
        role = self.sts.assume_cross_account_role(
            f'arn:{partition}:iam::{account_id}:'
            'role/adf-readonly-automation-role',
            'importer'
        )
        return CloudFormation(
            region=region,
            deployment_account_region=os.environ["AWS_REGION"],
            role=role,
            stack_name=stack_name,
            account_id=account_id,
        )

    # pylint: disable=unused-argument
    def resolve(self, lookup_str: str, random_filename: str) -> str:
        """
        Assumes that the lookup_str starts with 'import:'.

        This function will perform a lookup in CloudFormation
        to find the output value as requested by the lookup_str.

        Args:
            lookup_str (str): The lookup string that contains the
                `import:` lookup path.
            random_filename (str): The random filename, not used in this
                function.

        Returns:
            str: The value as looked up in CloudFormation.
        """
        optional = self._is_optional(lookup_str)
        if optional:
            LOGGER.info("Import %s is considered optional", lookup_str)
            # Remove the question mark
            lookup_str = lookup_str[:-1]
        if self.cache.exists(lookup_str):
            return self.cache.get(lookup_str)
        try:
            [_, account_id, region, stack_name, output_key] = (
                str(lookup_str).split(':')
            )
        except ValueError as error:
            raise ValueError(
                f"{lookup_str} is not a valid import string. "
                "Syntax should be: "
                "import:account_id:region:stack_name:output_key"
            ) from error
        try:
            stack = self._get_stack(account_id, region, stack_name)
            stack_output = stack.get_stack_output(output_key)
        except ClientError as client_error:
            LOGGER.info(
                "Could not retrieve CloudFormation output %s ran into "
                "a client error: %s",
                lookup_str,
                str(client_error),
            )
            if not optional:
                raise
            stack_output = None
        if stack_output is not None:
            LOGGER.info("Stack output value is %s", stack_output)
            self.cache.add(lookup_str, stack_output)
        elif not optional:
            raise LookupError(
                f"No Stack Output found on {account_id} in {region} "
                f"with stack name {stack_name} and "
                f"output key {output_key}"
            )
        return stack_output if stack_output is not None else ""

    # To enable an easy interface that could do lookups
    # whether a specific lookup string is supported or not it
    # should be instance based. Disabling: no-self-use warning
    def supports(self, lookup_str: str) -> bool:
        """
        Check if this resolver supports the lookup_str syntax.

        Args:
            lookup_str (str): The lookup string that might have import: or
                another resolver syntax.

        Returns:
            bool: True if this resolver supports the lookup_str syntax.
                In other words, the lookup_str starts with `import:`.
                False if not.
        """
        return lookup_str.startswith('import:')

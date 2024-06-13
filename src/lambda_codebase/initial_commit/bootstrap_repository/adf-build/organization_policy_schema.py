# Copyright 2022 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
Schema Validation for Organization Policy Files
"""

from schema import Schema, Or, Optional
from logger import configure_logger

LOGGER = configure_logger(__name__)

V2022_10_14_POLICY_TARGET_SCHEMA = Or([str], str)


V2022_10_14Schema = {
    "Targets": V2022_10_14_POLICY_TARGET_SCHEMA,
    Optional("Version", default="2022-10-14"): "2022-10-14",
    "PolicyName": str,
    "Policy": dict,
}

GENERIC_SCHEMA = {
    Optional("Version", default="2022-10-14"): "2022-10-14",
    object: object,
}

SCHEMA_MAP = {
    "2022-10-14": V2022_10_14Schema,
}


class OrgPolicySchema:
    def __init__(self, schema_to_validate: dict):
        LOGGER.info("Validating Policy Schema: %s", schema_to_validate)
        versioned_schema = Schema(GENERIC_SCHEMA).validate(schema_to_validate)
        LOGGER.info("Versioned Schema: %s", versioned_schema)
        self.schema = Schema(SCHEMA_MAP[versioned_schema["Version"]]).validate(
            versioned_schema
        )
        if isinstance(self.schema.get("Targets"), str):
            self.schema["Targets"] = [self.schema["Targets"]]

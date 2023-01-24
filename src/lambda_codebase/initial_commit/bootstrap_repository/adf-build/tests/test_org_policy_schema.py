"""
Tests organization policy schema.
"""

import unittest
from schema import SchemaError
import organization_policy_schema


class HappyTestCases(unittest.TestCase):
    def test_basic_schema_2022_10_14(self):
        schema = {
            "Targets": ["target1", "target2"],
            "PolicyName": "policy1",
            "Policy": {},
        }
        expected_schema = {
            "Targets": ["target1", "target2"],
            "PolicyName": "policy1",
            "Policy": {},
            "Version": "2022-10-14",
        }

        validated_policy = organization_policy_schema.OrgPolicySchema(schema).schema
        self.assertDictEqual(validated_policy, expected_schema)

    def test_basic_schema_2022_10_14_target_should_be_list(self):
        schema = {
            "Targets": "target1",
            "PolicyName": "policy1",
            "Policy": {},
            "Version": "2022-10-14",
        }
        expected_schema = {
            "Targets": ["target1"],
            "PolicyName": "policy1",
            "Policy": {},
            "Version": "2022-10-14",
        }

        validated_policy = organization_policy_schema.OrgPolicySchema(schema).schema
        self.assertDictEqual(validated_policy, expected_schema)


class SadTestCases(unittest.TestCase):
    def test_invalid_version(self):
        schema = {
            "Targets": ["target1", "target2"],
            "PolicyName": "policy1",
            "Policy": {},
            "Version": "2022-11-15",
        }

        with self.assertRaises(SchemaError):
            organization_policy_schema.OrgPolicySchema(schema)

    def test_invalid_field(self):
        schema = {
            "targets": ["target1", "target2"],
            "PolicyName": "policy1",
            "Policy": {},
            "Version": "2022-11-14",
        }

        with self.assertRaises(SchemaError):
            organization_policy_schema.OrgPolicySchema(schema)

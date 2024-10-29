"""
Tests for organizational policy v2
"""
import unittest
import os
import boto3
from botocore.stub import Stubber, ANY

from organization_policy_v2 import OrganizationPolicy

SCP_ONLY = {"scp": "SERVICE_CONTROL_POLICY"}
# This hurts me.
TOX_PATH_PREFIX = "/src/lambda_codebase/initial_commit/bootstrap_repository"
TEST_POLICY_PATH = "/adf-build/tests/adf-policies"
POLICY_PATH = (
    f"{TOX_PATH_PREFIX}{TEST_POLICY_PATH}"
    if not os.getenv("CODEPIPELINE_EXECUTION_ID")
    else TEST_POLICY_PATH
)


class FakeParamStore:
    params: dict()  # pylint: disable=R1735

    def __init__(self) -> None:
        self.params = {}

    def put_parameter(self, key, value):
        self.params[key] = value

    def fetch_parameter(self, key):
        return self.params[key]


class HappyTestCases(unittest.TestCase):
    def test_org_policy_campaign_creates_a_new_policy(self):
        org_client = boto3.client("organizations")
        org_stubber = Stubber(org_client)

        # No existing policy to look up
        org_stubber.add_response("list_policies", {"Policies": []})

        # loads up a target "TestOrg" and needs to get all policies it
        # this test case has no existing policies returned.
        org_stubber.add_response(
            "list_policies_for_target",
            {"Policies": []},
            {"TargetId": "ou-123456789", "Filter": "SERVICE_CONTROL_POLICY"},
        )

        # Creates a policy
        org_stubber.add_response(
            "create_policy",
            {
                "Policy": {
                    "PolicySummary": {
                        "Id": "fake-policy-id",
                        "Arn": "arn:aws:organizations:policy/fake-policy-id",
                        "Name": "TestPolicy",
                        "Description": "ADF Managed scp",
                        "Type": "SERVICE_CONTROL_POLICY",
                        "AwsManaged": False,
                    },
                    "Content": "fake-policy-content",
                }
            },
            {
                "Content": ANY,
                "Description": "ADF Managed scp",
                "Name": "TestPolicy",
                "Type": "SERVICE_CONTROL_POLICY",
            },
        )

        # Once created, the policy is then attached to the target
        org_stubber.add_response(
            "attach_policy",
            {},
            {"PolicyId": "fake-policy-id", "TargetId": "ou-123456789"},
        )

        org_stubber.activate()

        param_store = FakeParamStore()
        # No existing (legacy) SCPs have been put
        param_store.put_parameter("scp", "[]")

        policy_dir = f"{os.getcwd()}{POLICY_PATH}"

        org_policies_client = OrganizationPolicy(policy_dir)
        with self.assertLogs("organization_policy_v2") as log:
            org_policies_client.apply_policies(
                org_client, param_store, {}, {"TestOrg": "ou-123456789"}, SCP_ONLY
            )
            self.assertGreaterEqual(len(log.records), 0)

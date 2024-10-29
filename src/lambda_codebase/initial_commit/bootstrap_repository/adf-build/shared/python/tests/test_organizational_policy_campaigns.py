"""
Tests creation and execution of organizational policy campaigns
"""
import unittest
import json

import boto3
from botocore.stub import Stubber, ANY


from organization_policy_campaign import (
    OrganizationPolicyApplicationCampaign,
    OrganizationPolicyException,
)

POLICY_DEFINITIONS = [
    {
        "Targets": ["MyFirstOrg"],
        "Version": "2022-10-14",
        "PolicyName": "MyFirstPolicy",
        "Policy": {
            "Version": "2012-10-17",
            "Statement": [
                {"Effect": "Deny", "Action": "cloudtrail:Stop*", "Resource": "*"},
                {"Effect": "Allow", "Action": "*", "Resource": "*"},
                {
                    "Effect": "Deny",
                    "Action": [
                        "config:DeleteConfigRule",
                        "config:DeleteConfigurationRecorder",
                        "config:DeleteDeliveryChannel",
                        "config:Stop*",
                    ],
                    "Resource": "*",
                },
            ],
        },
    },
    {
        "Targets": ["MySecondOrg"],
        "Version": "2022-10-14",
        "PolicyName": "MySecondPolicy",
        "Policy": {
            "Version": "2012-10-17",
            "Statement": [
                {"Effect": "Deny", "Action": "cloudtrail:Stop*", "Resource": "*"},
                {"Effect": "Allow", "Action": "*", "Resource": "*"},
                {
                    "Effect": "Deny",
                    "Action": [
                        "config:DeleteConfigRule",
                        "config:DeleteConfigurationRecorder",
                        "config:DeleteDeliveryChannel",
                    ],
                    "Resource": "*",
                },
            ],
        },
    },
]

# pylint: disable=too-many-lines


class HappyTestCases(unittest.TestCase):
    def test_scp_campaign_creation_no_existing_policies(self):
        """
        Test case that covers the creation of two new SCPs that have one target
        each.
        """

        org_client = boto3.client("organizations")
        org_mapping = {"MyFirstOrg": "123456789012", "MySecondOrg": "09876543210"}
        stubber = Stubber(org_client)

        # No existing ADF managed policies.
        stubber.add_response("list_policies", {"Policies": []})

        # When the target object is created,
        # it will query to see if it has any policies already
        stubber.add_response(
            "list_policies_for_target",
            {"Policies": []},
            {"TargetId": "123456789012", "Filter": "SERVICE_CONTROL_POLICY"},
        )
        stubber.add_response(
            "list_policies_for_target",
            {"Policies": []},
            {"TargetId": "09876543210", "Filter": "SERVICE_CONTROL_POLICY"},
        )

        # Create Policy API Call
        stubber.add_response(
            "create_policy",
            {
                "Policy": {
                    "PolicySummary": {
                        "Id": "fake-policy-id",
                        "Arn": "arn:aws:organizations:policy/fake-policy-id",
                        "Name": "MyFirstPolicy",
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
                "Name": "MyFirstPolicy",
                "Type": "SERVICE_CONTROL_POLICY",
            },
        )

        # Once created, the policy is attached to the target
        stubber.add_response(
            "attach_policy",
            {},
            {"PolicyId": "fake-policy-id", "TargetId": "123456789012"},
        )

        # Creation and attachment of second policy
        stubber.add_response(
            "create_policy",
            {
                "Policy": {
                    "PolicySummary": {
                        "Id": "fake-policy-id-2",
                        "Arn": "arn:aws:organizations:policy/fake-policy-id-2",
                        "Name": "MySecondPolicy",
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
                "Name": "MySecondPolicy",
                "Type": "SERVICE_CONTROL_POLICY",
            },
        )
        stubber.add_response(
            "attach_policy",
            {},
            {"PolicyId": "fake-policy-id-2", "TargetId": "09876543210"},
        )

        stubber.activate()

        policy_campaign = OrganizationPolicyApplicationCampaign(
            "SERVICE_CONTROL_POLICY", org_mapping, {}, org_client
        )

        for _policy in POLICY_DEFINITIONS:
            policy = policy_campaign.get_policy(
                _policy.get("PolicyName"), _policy.get("Policy")
            )
            self.assertEqual(0, len(policy.targets_requiring_attachment))
            policy.set_targets(
                [policy_campaign.get_target(t) for t in _policy.get("Targets")]
            )
            self.assertEqual(1, len(policy.targets_requiring_attachment))

        policy_campaign.apply()

    def test_scp_campaign_creation_one_existing_policy_different_content(self):
        org_client = boto3.client("organizations")
        org_mapping = {"MyFirstOrg": "123456789012", "MySecondOrg": "09876543210"}
        stubber = Stubber(org_client)

        # One pre-existing ADF managed policy
        stubber.add_response(
            "list_policies",
            {
                "Policies": [
                    {
                        "Id": "fake-policy-1",
                        "Arn": "arn:aws:organizations:policy/fake-policy-1",
                        "Name": "MyFirstPolicy",
                        "Description": "ADF Managed scp",
                        "Type": "SERVICE_CONTROL_POLICY",
                        "AwsManaged": False,
                    }
                ]
            },
        )

        # When a preexisting policy is loaded - describe policy is used to get
        # the existing policy content.
        stubber.add_response(
            "describe_policy",
            {
                "Policy": {
                    "PolicySummary": {},
                    "Content": json.dumps({"old-policy": "content"}),
                }
            },
            {"PolicyId": "fake-policy-1"},
        )

        # When loading a policy object that exists already, this API call is
        # used to populate the list of existing targets.
        stubber.add_response(
            "list_targets_for_policy",
            {"Targets": []},
            {"PolicyId": "fake-policy-1"},
        )

        # Creation of target object - Query for existing policies
        stubber.add_response(
            "list_policies_for_target",
            {"Policies": []},
            {"TargetId": "123456789012", "Filter": "SERVICE_CONTROL_POLICY"},
        )
        stubber.add_response(
            "list_policies_for_target",
            {"Policies": []},
            {"TargetId": "09876543210", "Filter": "SERVICE_CONTROL_POLICY"},
        )

        # Creates the second policy and attaches the policy to the target
        stubber.add_response(
            "create_policy",
            {
                "Policy": {
                    "PolicySummary": {
                        "Id": "fake-policy-id-2",
                        "Arn": "arn:aws:organizations:policy/fake-policy-id-2",
                        "Name": "MySecondPolicy",
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
                "Name": "MySecondPolicy",
                "Type": "SERVICE_CONTROL_POLICY",
            },
        )
        stubber.add_response(
            "attach_policy",
            {},
            {"PolicyId": "fake-policy-id-2", "TargetId": "09876543210"},
        )

        # Update the content of the existing policy
        stubber.add_response(
            "update_policy",
            {
                "Policy": {
                    "PolicySummary": {
                        "Id": "fake-policy-1",
                        "Arn": "arn:aws:organizations:policy/fake-policy-1",
                        "Name": "MyFirstPolicy",
                        "Description": "ADF Managed scp",
                        "Type": "SERVICE_CONTROL_POLICY",
                        "AwsManaged": False,
                    },
                    "Content": "fake-policy-content",
                }
            },
            {
                "PolicyId": "fake-policy-1",
                "Content": json.dumps(POLICY_DEFINITIONS[0].get("Policy")),
            },
        )

        # Attach 1st policy to the target as part of the update process.
        stubber.add_response(
            "attach_policy",
            {},
            {"PolicyId": "fake-policy-1", "TargetId": "123456789012"},
        )
        stubber.activate()

        policy_campaign = OrganizationPolicyApplicationCampaign(
            "SERVICE_CONTROL_POLICY", org_mapping, {}, org_client
        )

        for _policy in POLICY_DEFINITIONS:
            policy = policy_campaign.get_policy(
                _policy.get("PolicyName"), _policy.get("Policy")
            )
            self.assertEqual(0, len(policy.targets_requiring_attachment))
            policy.set_targets(
                [policy_campaign.get_target(t) for t in _policy.get("Targets")]
            )
            self.assertEqual(1, len(policy.targets_requiring_attachment))

        policy_campaign.apply()

    def test_scp_campaign_creation_one_existing_policy(self):
        org_client = boto3.client("organizations")
        org_mapping = {"MyFirstOrg": "123456789012", "MySecondOrg": "09876543210"}
        stubber = Stubber(org_client)

        # One pre-existing ADF managed policy
        stubber.add_response(
            "list_policies",
            {
                "Policies": [
                    {
                        "Id": "fake-policy-1",
                        "Arn": "arn:aws:organizations:policy/fake-policy-1",
                        "Name": "MyFirstPolicy",
                        "Description": "ADF Managed scp",
                        "Type": "SERVICE_CONTROL_POLICY",
                        "AwsManaged": False,
                    }
                ]
            },
        )

        # When a preexisting policy is loaded - describe policy is used to get
        # the existing policy content.
        stubber.add_response(
            "describe_policy",
            {
                "Policy": {
                    "PolicySummary": {},
                    "Content": json.dumps(POLICY_DEFINITIONS[0].get("Policy")),
                }
            },
            {"PolicyId": "fake-policy-1"},
        )

        # When loading a policy object that exists already, this API call is
        # used to populate the list of existing targets.
        stubber.add_response(
            "list_targets_for_policy",
            {"Targets": []},
            {"PolicyId": "fake-policy-1"},
        )

        # Creation of target object - Query for existing policies
        stubber.add_response(
            "list_policies_for_target",
            {"Policies": []},
            {"TargetId": "123456789012", "Filter": "SERVICE_CONTROL_POLICY"},
        )
        stubber.add_response(
            "list_policies_for_target",
            {"Policies": []},
            {"TargetId": "09876543210", "Filter": "SERVICE_CONTROL_POLICY"},
        )

        # Creates the second policy and attaches the policy to the target
        stubber.add_response(
            "create_policy",
            {
                "Policy": {
                    "PolicySummary": {
                        "Id": "fake-policy-id-2",
                        "Arn": "arn:aws:organizations:policy/fake-policy-id-2",
                        "Name": "MySecondPolicy",
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
                "Name": "MySecondPolicy",
                "Type": "SERVICE_CONTROL_POLICY",
            },
        )
        stubber.add_response(
            "attach_policy",
            {},
            {"PolicyId": "fake-policy-id-2", "TargetId": "09876543210"},
        )

        # Attach 1st policy to the target as part of the update process.
        stubber.add_response(
            "attach_policy",
            {},
            {"PolicyId": "fake-policy-1", "TargetId": "123456789012"},
        )
        stubber.activate()

        policy_campaign = OrganizationPolicyApplicationCampaign(
            "SERVICE_CONTROL_POLICY", org_mapping, {}, org_client
        )

        for _policy in POLICY_DEFINITIONS:
            policy = policy_campaign.get_policy(
                _policy.get("PolicyName"), _policy.get("Policy")
            )
            self.assertEqual(0, len(policy.targets_requiring_attachment))
            policy.set_targets(
                [policy_campaign.get_target(t) for t in _policy.get("Targets")]
            )
            self.assertEqual(1, len(policy.targets_requiring_attachment))

        policy_campaign.apply()

    def test_scp_campaign_creation_one_existing_policy_with_existing_target(self):
        policy_definitions = [
            {
                "Targets": ["MyFirstOrg", "MySecondOrg", "MyThirdOrg"],
                "Version": "2022-10-14",
                "PolicyName": "MyFirstPolicy",
                "Policy": {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Effect": "Deny",
                            "Action": "cloudtrail:Stop*",
                            "Resource": "*",
                        },
                        {"Effect": "Allow", "Action": "*", "Resource": "*"},
                        {
                            "Effect": "Deny",
                            "Action": [
                                "config:DeleteConfigRule",
                                "config:DeleteConfigurationRecorder",
                                "config:DeleteDeliveryChannel",
                                "config:Stop*",
                            ],
                            "Resource": "*",
                        },
                    ],
                },
            }
        ]
        org_client = boto3.client("organizations")
        org_mapping = {
            "MyFirstOrg": "123456789012",
            "MySecondOrg": "09876543210",
            "MyThirdOrg": "11223344556",
        }
        stubber = Stubber(org_client)

        # One pre-existing ADF managed policy
        stubber.add_response(
            "list_policies",
            {
                "Policies": [
                    {
                        "Id": "fake-policy-1",
                        "Arn": "arn:aws:organizations:policy/fake-policy-1",
                        "Name": "MyFirstPolicy",
                        "Description": "ADF Managed scp",
                        "Type": "SERVICE_CONTROL_POLICY",
                        "AwsManaged": False,
                    }
                ]
            },
        )

        # When a preexisting policy is loaded - describe policy is used to get
        # the existing policy content.
        stubber.add_response(
            "describe_policy",
            {
                "Policy": {
                    "PolicySummary": {},
                    "Content": json.dumps(POLICY_DEFINITIONS[0].get("Policy")),
                }
            },
            {"PolicyId": "fake-policy-1"},
        )

        # When loading a policy object that exists already, this API call is
        # used to populate the list of existing targets.
        stubber.add_response(
            "list_targets_for_policy",
            {
                "Targets": [
                    {
                        "TargetId": "11223344556",
                        "Arn": "arn:aws:organizations:account11223344556",
                        "Name": "MyThirdOrg",
                        "Type": "ORGANIZATIONAL_UNIT",
                    }
                ]
            },
            {"PolicyId": "fake-policy-1"},
        )

        # Creation of target object - Query for existing policies (three targets)
        stubber.add_response(
            "list_policies_for_target",
            {"Policies": []},
            {"TargetId": "123456789012", "Filter": "SERVICE_CONTROL_POLICY"},
        )

        stubber.add_response(
            "list_policies_for_target",
            {"Policies": []},
            {"TargetId": "09876543210", "Filter": "SERVICE_CONTROL_POLICY"},
        )

        stubber.add_response(
            "list_policies_for_target",
            {"Policies": []},
            {"TargetId": "11223344556", "Filter": "SERVICE_CONTROL_POLICY"},
        )

        # Attach the policy to two OUs - MyFirstOrg / MySecondOrg

        stubber.add_response(
            "attach_policy",
            {},
            {"PolicyId": "fake-policy-1", "TargetId": "123456789012"},
        )

        stubber.add_response(
            "attach_policy",
            {},
            {"PolicyId": "fake-policy-1", "TargetId": "09876543210"},
        )

        stubber.activate()
        policy_campaign = OrganizationPolicyApplicationCampaign(
            "SERVICE_CONTROL_POLICY", org_mapping, {}, org_client
        )

        for _policy in policy_definitions:
            policy = policy_campaign.get_policy(
                _policy.get("PolicyName"), _policy.get("Policy")
            )
            self.assertEqual(0, len(policy.targets_requiring_attachment))
            policy.set_targets(
                [policy_campaign.get_target(t) for t in _policy.get("Targets")]
            )
            self.assertEqual(2, len(policy.targets_requiring_attachment))

        policy_campaign.apply()

    def test_scp_campaign_creation_one_existing_policy_with_existing_target_deletion(
        self,
    ):
        policy_definitions = [
            {
                "Targets": ["MyFirstOrg", "MySecondOrg"],
                "Version": "2022-10-14",
                "PolicyName": "MyFirstPolicy",
                "Policy": {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Effect": "Deny",
                            "Action": "cloudtrail:Stop*",
                            "Resource": "*",
                        },
                        {"Effect": "Allow", "Action": "*", "Resource": "*"},
                        {
                            "Effect": "Deny",
                            "Action": [
                                "config:DeleteConfigRule",
                                "config:DeleteConfigurationRecorder",
                                "config:DeleteDeliveryChannel",
                                "config:Stop*",
                            ],
                            "Resource": "*",
                        },
                    ],
                },
            }
        ]
        org_client = boto3.client("organizations")
        org_mapping = {
            "MyFirstOrg": "123456789012",
            "MySecondOrg": "09876543210",
            "MyThirdOrg": "11223344556",
        }
        stubber = Stubber(org_client)

        # One pre-existing ADF managed policy
        stubber.add_response(
            "list_policies",
            {
                "Policies": [
                    {
                        "Id": "fake-policy-1",
                        "Arn": "arn:aws:organizations:policy/fake-policy-1",
                        "Name": "MyFirstPolicy",
                        "Description": "ADF Managed scp",
                        "Type": "SERVICE_CONTROL_POLICY",
                        "AwsManaged": False,
                    }
                ]
            },
        )

        # When a preexisting policy is loaded - describe policy is used to get
        # the existing policy content.
        stubber.add_response(
            "describe_policy",
            {
                "Policy": {
                    "PolicySummary": {},
                    "Content": json.dumps(POLICY_DEFINITIONS[0].get("Policy")),
                }
            },
            {"PolicyId": "fake-policy-1"},
        )

        # When loading a policy object that exists already, this API call is
        # used to populate the list of existing targets.
        stubber.add_response(
            "list_targets_for_policy",
            {
                "Targets": [
                    {
                        "TargetId": "11223344556",
                        "Arn": "arn:aws:organizations:account11223344556",
                        "Name": "MyThirdOrg",
                        "Type": "ORGANIZATIONAL_UNIT",
                    }
                ]
            },
            {"PolicyId": "fake-policy-1"},
        )

        # Creation of target object - Query for existing policies (two targets)
        stubber.add_response(
            "list_policies_for_target",
            {"Policies": []},
            {"TargetId": "123456789012", "Filter": "SERVICE_CONTROL_POLICY"},
        )

        stubber.add_response(
            "list_policies_for_target",
            {"Policies": []},
            {"TargetId": "09876543210", "Filter": "SERVICE_CONTROL_POLICY"},
        )

        # Attach the policy to two OUs - MyFirstOrg / MySecondOrg

        stubber.add_response(
            "attach_policy",
            {},
            {"PolicyId": "fake-policy-1", "TargetId": "123456789012"},
        )

        stubber.add_response(
            "attach_policy",
            {},
            {"PolicyId": "fake-policy-1", "TargetId": "09876543210"},
        )

        stubber.add_response(
            "detach_policy",
            {},
            {"PolicyId": "fake-policy-1", "TargetId": "11223344556"},
        )

        stubber.activate()

        policy_campaign = OrganizationPolicyApplicationCampaign(
            "SERVICE_CONTROL_POLICY", org_mapping, {}, org_client
        )

        for _policy in policy_definitions:
            policy = policy_campaign.get_policy(
                _policy.get("PolicyName"), _policy.get("Policy")
            )
            self.assertEqual(0, len(policy.targets_requiring_attachment))
            policy.set_targets(
                [policy_campaign.get_target(t) for t in _policy.get("Targets")]
            )
            self.assertEqual(2, len(policy.targets_requiring_attachment))

        policy_campaign.apply()

    def test_scp_campaign_creation_no_existing_policies_targets_have_default_policy(
        self,
    ):
        """
        Test case that covers the creation of two new SCPs that have one target with the default SCP
        each.
        """

        org_client = boto3.client("organizations")
        org_mapping = {"MyFirstOrg": "123456789012", "MySecondOrg": "09876543210"}
        stubber = Stubber(org_client)

        # No existing ADF managed policies.
        stubber.add_response("list_policies", {"Policies": []})

        # When the target object is created,
        # it will query to see if it has any policies already
        stubber.add_response(
            "list_policies_for_target",
            {
                "Policies": [
                    {
                        "Id": "p-FullAWSAccess",
                        "Arn": "arn:aws:organization:policy/p-FullAWSAccess",
                        "Name": "FullAWSAccess",
                        "Description": "FullAWSAccess",
                        "Type": "SERVICE_CONTROL_POLICY",
                        "AwsManaged": True,
                    }
                ]
            },
            {"TargetId": "123456789012", "Filter": "SERVICE_CONTROL_POLICY"},
        )
        stubber.add_response(
            "list_policies_for_target",
            {"Policies": []},
            {"TargetId": "09876543210", "Filter": "SERVICE_CONTROL_POLICY"},
        )

        # Create Policy API Call
        stubber.add_response(
            "create_policy",
            {
                "Policy": {
                    "PolicySummary": {
                        "Id": "fake-policy-id",
                        "Arn": "arn:aws:organizations:policy/fake-policy-id",
                        "Name": "MyFirstPolicy",
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
                "Name": "MyFirstPolicy",
                "Type": "SERVICE_CONTROL_POLICY",
            },
        )

        # Once created, the policy is attached to the target
        stubber.add_response(
            "attach_policy",
            {},
            {"PolicyId": "fake-policy-id", "TargetId": "123456789012"},
        )
        # Once the other policy is attached, we detach the default policy
        stubber.add_response(
            "detach_policy",
            {},
            {"PolicyId": "p-FullAWSAccess", "TargetId": "123456789012"},
        )

        # Creation and attachment of second policy
        stubber.add_response(
            "create_policy",
            {
                "Policy": {
                    "PolicySummary": {
                        "Id": "fake-policy-id-2",
                        "Arn": "arn:aws:organizations:policy/fake-policy-id-2",
                        "Name": "MySecondPolicy",
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
                "Name": "MySecondPolicy",
                "Type": "SERVICE_CONTROL_POLICY",
            },
        )
        stubber.add_response(
            "attach_policy",
            {},
            {"PolicyId": "fake-policy-id-2", "TargetId": "09876543210"},
        )

        stubber.activate()

        policy_campaign = OrganizationPolicyApplicationCampaign(
            "SERVICE_CONTROL_POLICY",
            org_mapping,
            {"keep-default-scp": "disabled"},
            org_client,
        )

        for _policy in POLICY_DEFINITIONS:
            policy = policy_campaign.get_policy(
                _policy.get("PolicyName"), _policy.get("Policy")
            )
            self.assertEqual(0, len(policy.targets_requiring_attachment))
            policy.set_targets(
                [policy_campaign.get_target(t) for t in _policy.get("Targets")]
            )
            self.assertEqual(1, len(policy.targets_requiring_attachment))

        policy_campaign.apply()

    def test_scp_campaign_creation_one_existing_policy_not_in_definitions(self):
        org_client = boto3.client("organizations")
        org_mapping = {"MyFirstOrg": "123456789012", "MySecondOrg": "09876543210"}
        stubber = Stubber(org_client)

        # One pre-existing ADF managed policy
        stubber.add_response(
            "list_policies",
            {
                "Policies": [
                    {
                        "Id": "fake-policy-1",
                        "Arn": "arn:aws:organizations:policy/fake-policy-1",
                        "Name": "MyFirstPolicy",
                        "Description": "ADF Managed scp",
                        "Type": "SERVICE_CONTROL_POLICY",
                        "AwsManaged": False,
                    }
                ]
            },
        )

        stubber.add_response(
            "list_policies_for_target",
            {"Policies": []},
            {"TargetId": "09876543210", "Filter": "SERVICE_CONTROL_POLICY"},
        )

        # Creates the second policy and attaches the policy to the target
        stubber.add_response(
            "create_policy",
            {
                "Policy": {
                    "PolicySummary": {
                        "Id": "fake-policy-id-2",
                        "Arn": "arn:aws:organizations:policy/fake-policy-id-2",
                        "Name": "MySecondPolicy",
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
                "Name": "MySecondPolicy",
                "Type": "SERVICE_CONTROL_POLICY",
            },
        )
        stubber.add_response(
            "attach_policy",
            {},
            {"PolicyId": "fake-policy-id-2", "TargetId": "09876543210"},
        )

        stubber.add_response(
            "list_targets_for_policy",
            {
                "Targets": [
                    {
                        "TargetId": "11223344556",
                        "Arn": "arn:aws:organizations:account11223344556",
                        "Name": "MyThirdOrg",
                        "Type": "ORGANIZATIONAL_UNIT",
                    }
                ]
            },
            {"PolicyId": "fake-policy-1"},
        )

        stubber.add_response(
            "detach_policy",
            {},
            {"PolicyId": "fake-policy-1", "TargetId": "11223344556"},
        )
        stubber.add_response(
            "delete_policy",
            {},
            {"PolicyId": "fake-policy-1"},
        )
        stubber.activate()

        policy_campaign = OrganizationPolicyApplicationCampaign(
            "SERVICE_CONTROL_POLICY", org_mapping, {}, org_client
        )

        for _policy in POLICY_DEFINITIONS[1:]:
            policy = policy_campaign.get_policy(
                _policy.get("PolicyName"), _policy.get("Policy")
            )
            self.assertEqual(0, len(policy.targets_requiring_attachment))
            policy.set_targets(
                [policy_campaign.get_target(t) for t in _policy.get("Targets")]
            )
            self.assertEqual(1, len(policy.targets_requiring_attachment))

        policy_campaign.apply()
        stubber.assert_no_pending_responses()


class SadTestCases(unittest.TestCase):
    def test_scp_campaign_creation_access_denied_error_fetching_policies(self):
        org_client = boto3.client("organizations")
        org_mapping = {"MyFirstOrg": "123456789012", "MySecondOrg": "09876543210"}
        stubber = Stubber(org_client)

        stubber.add_client_error(
            method="list_policies",
            service_error_code="AccessDeniedException",
            service_message="Access Denied",
        )

        stubber.activate()
        with self.assertRaises(OrganizationPolicyException):
            OrganizationPolicyApplicationCampaign(
                "SERVICE_CONTROL_POLICY", org_mapping, {}, org_client
            )

    def test_scp_campaign_creation_orgs_not_in_use_fetching_policies(self):
        org_client = boto3.client("organizations")
        org_mapping = {"MyFirstOrg": "123456789012", "MySecondOrg": "09876543210"}
        stubber = Stubber(org_client)

        stubber.add_client_error(
            method="list_policies",
            service_error_code="AWSOrganizationsNotInUseException",
            service_message="AWSOrganizationsNotInUseException",
        )

        stubber.activate()
        with self.assertRaises(OrganizationPolicyException):
            OrganizationPolicyApplicationCampaign(
                "SERVICE_CONTROL_POLICY", org_mapping, {}, org_client
            )

    def test_scp_campaign_creation_invalid_input_fetching_policies(self):
        org_client = boto3.client("organizations")
        org_mapping = {"MyFirstOrg": "123456789012", "MySecondOrg": "09876543210"}
        stubber = Stubber(org_client)

        stubber.add_client_error(
            method="list_policies",
            service_error_code="InvalidInputException",
            service_message="InvalidInputException",
        )

        stubber.activate()
        with self.assertRaises(OrganizationPolicyException):
            OrganizationPolicyApplicationCampaign(
                "SERVICE_CONTROL_POLICY", org_mapping, {}, org_client
            )

    def test_scp_campaign_creations_service_exception_fetching_policies(self):
        org_client = boto3.client("organizations")
        org_mapping = {"MyFirstOrg": "123456789012", "MySecondOrg": "09876543210"}
        stubber = Stubber(org_client)

        stubber.add_client_error(
            method="list_policies",
            service_error_code="ServiceException",
            service_message="ServiceException",
        )

        stubber.activate()
        with self.assertRaises(OrganizationPolicyException):
            OrganizationPolicyApplicationCampaign(
                "SERVICE_CONTROL_POLICY", org_mapping, {}, org_client
            )

    def test_scp_campaign_creations_too_many_requests_fetching_policies(self):
        org_client = boto3.client("organizations")
        org_mapping = {"MyFirstOrg": "123456789012", "MySecondOrg": "09876543210"}
        stubber = Stubber(org_client)

        stubber.add_client_error(
            method="list_policies",
            service_error_code="TooManyRequestsException",
            service_message="TooManyRequestsException",
        )

        stubber.activate()
        with self.assertRaises(OrganizationPolicyException):
            OrganizationPolicyApplicationCampaign(
                "SERVICE_CONTROL_POLICY", org_mapping, {}, org_client
            )

    def test_scp_campaign_creation_load_policy_access_denied(self):
        org_client = boto3.client("organizations")
        org_mapping = {"MyFirstOrg": "123456789012", "MySecondOrg": "09876543210"}
        stubber = Stubber(org_client)

        # One pre-existing ADF managed policy
        stubber.add_response(
            "list_policies",
            {
                "Policies": [
                    {
                        "Id": "fake-policy-1",
                        "Arn": "arn:aws:organizations:policy/fake-policy-1",
                        "Name": "MyFirstPolicy",
                        "Description": "ADF Managed scp",
                        "Type": "SERVICE_CONTROL_POLICY",
                        "AwsManaged": False,
                    }
                ]
            },
        )

        # When a preexisting policy is loaded - describe policy is used to get
        # the existing policy content.
        stubber.add_client_error(
            method="describe_policy",
            service_error_code="AccessDeniedException",
            service_message="Access Denied",
        )

        # Attach 1st policy to the target as part of the update process.
        stubber.add_response(
            "attach_policy",
            {},
            {"PolicyId": "fake-policy-1", "TargetId": "123456789012"},
        )
        stubber.activate()

        policy_campaign = OrganizationPolicyApplicationCampaign(
            "SERVICE_CONTROL_POLICY", org_mapping, {}, org_client
        )

        with self.assertRaises(OrganizationPolicyException):
            for _policy in POLICY_DEFINITIONS:
                policy_campaign.get_policy(
                    _policy.get("PolicyName"), _policy.get("Policy")
                )

    def test_policy_detachment_error_handling_access_denied(self):
        org_client = boto3.client("organizations")
        org_mapping = {
            "MyFirstOrg": "11223344556",
        }
        stubber = Stubber(org_client)

        # One pre-existing ADF managed policy
        stubber.add_response(
            "list_policies",
            {
                "Policies": [
                    {
                        "Id": "fake-policy-3",
                        "Arn": "arn:aws:organizations:policy/fake-policy-1",
                        "Name": "MyFirstPolicy",
                        "Description": "ADF Managed scp",
                        "Type": "SERVICE_CONTROL_POLICY",
                        "AwsManaged": False,
                    }
                ]
            },
        )

        stubber.add_response(
            "list_targets_for_policy",
            {
                "Targets": [
                    {
                        "TargetId": "11223344556",
                        "Arn": "arn:aws:organizations:account11223344556",
                        "Name": "MyFirstOrg",
                        "Type": "ORGANIZATIONAL_UNIT",
                    }
                ]
            },
            {"PolicyId": "fake-policy-3"},
        )

        stubber.add_client_error(
            method="detach_policy",
            service_error_code="AccessDeniedException",
            service_message="Access Denied",
            expected_params={"PolicyId": "fake-policy-3", "TargetId": "11223344556"},
        )

        stubber.activate()
        policy_campaign = OrganizationPolicyApplicationCampaign(
            "SERVICE_CONTROL_POLICY", org_mapping, {}, org_client
        )
        with self.assertRaises(OrganizationPolicyException):
            policy_campaign.apply()

        stubber.assert_no_pending_responses()

    def test_policy_detachment_error_handling_policy_not_attached(self):
        org_client = boto3.client("organizations")
        org_mapping = {
            "MyFirstOrg": "11223344556",
        }
        stubber = Stubber(org_client)

        # One pre-existing ADF managed policy
        stubber.add_response(
            "list_policies",
            {
                "Policies": [
                    {
                        "Id": "fake-policy-3",
                        "Arn": "arn:aws:organizations:policy/fake-policy-1",
                        "Name": "MyFirstPolicy",
                        "Description": "ADF Managed scp",
                        "Type": "SERVICE_CONTROL_POLICY",
                        "AwsManaged": False,
                    }
                ]
            },
        )

        stubber.add_response(
            "list_targets_for_policy",
            {
                "Targets": [
                    {
                        "TargetId": "11223344556",
                        "Arn": "arn:aws:organizations:account11223344556",
                        "Name": "MyFirstOrg",
                        "Type": "ORGANIZATIONAL_UNIT",
                    }
                ]
            },
            {"PolicyId": "fake-policy-3"},
        )

        stubber.add_client_error(
            method="detach_policy",
            service_error_code="PolicyNotAttachedException",
            service_message="Policy Not Attached",
            expected_params={"PolicyId": "fake-policy-3", "TargetId": "11223344556"},
        )

        stubber.add_response(
            "delete_policy",
            {},
            {"PolicyId": "fake-policy-3"},
        )

        stubber.activate()
        policy_campaign = OrganizationPolicyApplicationCampaign(
            "SERVICE_CONTROL_POLICY", org_mapping, {}, org_client
        )
        ex_r = (
            "WARNING:organization_policy_campaign:Error detaching policy"
                " MyFirstPolicy (fake-policy-3) from target 11223344556: "
                "Policy Not Attached"
                )

        with self.assertLogs("organization_policy_campaign", "WARNING") as log:
            policy_campaign.apply()
            self.assertIn(
                ex_r,
                log.output,
            )

        stubber.assert_no_pending_responses()

import unittest
import json
import boto3
from botocore.stub import Stubber, ANY


from organisation_policy_campaign import OrganizationPolicyApplicationCampaign

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
                        "Arn": "arn:aws:organisations:policy/fake-policy-id",
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
                        "Arn": "arn:aws:organisations:policy/fake-policy-id-2",
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
                        "Arn": "arn:aws:organisations:policy/fake-policy-id-2",
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
                        "Arn": "arn:aws:organisation:policy/p-FullAWSAccess",
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
                        "Arn": "arn:aws:organisations:policy/fake-policy-id",
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
                        "Arn": "arn:aws:organisations:policy/fake-policy-id-2",
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
        assert 1 == 2

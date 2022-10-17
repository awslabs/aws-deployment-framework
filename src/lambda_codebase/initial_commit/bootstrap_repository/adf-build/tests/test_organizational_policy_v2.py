import unittest
import boto3
from botocore.stub import Stubber, ANY


from organization_policy_v2 import (
    OrganizationPolicyApplicationCampaign
)

POLICY_DEFINITIONS = [
    {
	"Targets": ["MyFirstOrg"],
	"Version": "2022-10-14",
	"PolicyName": "PolicyOne",
	"Policy": {
		"Version": "2012-10-17",
		"Statement": [{
				"Effect": "Deny",
				"Action": "cloudtrail:Stop*",
				"Resource": "*"
			},
			{
				"Effect": "Allow",
				"Action": "*",
				"Resource": "*"
			},
			{
				"Effect": "Deny",
				"Action": [
					"config:DeleteConfigRule",
					"config:DeleteConfigurationRecorder",
					"config:DeleteDeliveryChannel",
					"config:Stop*"
				],
				"Resource": "*"
			}
		]
	}
},
{
	"Targets": ["MySecondOrg"],
	"Version": "2022-10-14",
	"PolicyName": "MySecondPolicy",
	"Policy": {
		"Version": "2012-10-17",
		"Statement": [{
				"Effect": "Deny",
				"Action": "cloudtrail:Stop*",
				"Resource": "*"
			},
			{
				"Effect": "Allow",
				"Action": "*",
				"Resource": "*"
			},
			{
				"Effect": "Deny",
				"Action": [
					"config:DeleteConfigRule",
					"config:DeleteConfigurationRecorder",
					"config:DeleteDeliveryChannel",
					"config:Stop*"
				],
				"Resource": "*"
			}
		]
	}
}
]


class HappyTestCases(unittest.TestCase):
    def test_scp_campaign_creation_no_existing_policies(self):
        org_client = boto3.client("organizations")
        org_mapping = {"MyFirstOrg": "123456789012", "MySecondOrg": "09876543210"}
        stubber = Stubber(org_client)
        stubber.add_response(
                    "list_policies",
                    {"Policies": []}
                )
        stubber.add_response(
                    "list_policies_for_target",
                    {"Policies": []},
                    {"TargetId": "123456789012", "Filter":"SERVICE_CONTROL_POLICY"}
                )
        stubber.add_response(
                    "list_policies_for_target",
                    {"Policies": []},
                    {"TargetId": "09876543210", "Filter":"SERVICE_CONTROL_POLICY"}
                )
        stubber.add_response(
                    "create_policy",
                    {"Policy": {
                        "PolicySummary": {
                            "Id": "fake-policy-id",
                            "Arn": "arn:aws:organisations:policy/fake-policy-id",
                            "Name": "MyFirstPolicy",
                            "Description": "ADF Managed scp",
                            "Type": "SERVICE_CONTROL_POLICY",
                            "AwsManaged": False

                        },
                        "Content": "fake-policy-content"
                    }},
                    {"Content": ANY, "Description":"ADF Managed scp", "Name": "PolicyOne", "Type": "SERVICE_CONTROL_POLICY"}
                )
        stubber.add_response(
                    "attach_policy",
                    {},
                    {"PolicyId": "fake-policy-id", "TargetId": "123456789012"}
                )
        stubber.add_response(
                    "create_policy",
                    {"Policy": {
                        "PolicySummary": {
                            "Id": "fake-policy-id-2",
                            "Arn": "arn:aws:organisations:policy/fake-policy-id-2",
                            "Name": "MySecondPolicy",
                            "Description": "ADF Managed scp",
                            "Type": "SERVICE_CONTROL_POLICY",
                            "AwsManaged": False

                        },
                        "Content": "fake-policy-content"
                    }},
                    {"Content": ANY, "Description":"ADF Managed scp", "Name": "MySecondPolicy", "Type": "SERVICE_CONTROL_POLICY"}
                )
        stubber.activate()

        policy_campaign = OrganizationPolicyApplicationCampaign(
            "SERVICE_CONTROL_POLICY", org_mapping, org_client
        )

        for _policy in POLICY_DEFINITIONS:
            policy = policy_campaign.get_policy(_policy.get("PolicyName"), _policy.get("Policy"))
            policy.set_targets([policy_campaign.get_target(t) for t in  _policy.get("Targets")])


        self.assertEqual(len(policy_campaign.policies_to_be_created), 2)

        policy_campaign.apply()


        assert 1 == 2

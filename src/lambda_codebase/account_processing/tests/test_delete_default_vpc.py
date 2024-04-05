"""
Tests the delete_default_vpc lambda
"""

import unittest
from unittest.mock import MagicMock, patch
from delete_default_vpc import find_default_vpc
from botocore.exceptions import ClientError


class TestFindDefaultVPC(unittest.TestCase):

    @patch('delete_default_vpc.patch_all')
    # pylint: disable=unused-argument
    def test_find_default_vpc(self, mock_patch_all):
        # Create a mock ec2_client
        mock_ec2_client = MagicMock()

        # Define the side effects for describe_vpcs method
        side_effects = [
            ClientError({'Error': {'Code': 'MockTestError'}}, 'describe_vpcs'),
            ClientError({'Error': {'Code': 'MockTestError'}}, 'describe_vpcs'),
            {"Vpcs": [
                {"VpcId": "vpc-123", "IsDefault": False},
                {"VpcId": "vpc-456", "IsDefault": True},
                {"VpcId": "vpc-789", "IsDefault": False}
            ]}
        ]

        # Set side_effect for the mock ec2_client.describe_vpcs
        mock_ec2_client.describe_vpcs.side_effect = side_effects

        # Call the function with the mock ec2_client
        default_vpc_id = find_default_vpc(mock_ec2_client)

        # Check if the correct default VPC ID is returned
        self.assertEqual(default_vpc_id, "vpc-456")

        # Check if describe_vpcs method is called 3 times
        self.assertEqual(mock_ec2_client.describe_vpcs.call_count, 3)


if __name__ == '__main__':
    unittest.main()

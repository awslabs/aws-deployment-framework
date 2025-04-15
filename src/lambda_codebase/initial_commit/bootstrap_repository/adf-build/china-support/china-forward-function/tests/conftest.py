"""
conftest file
"""
import pytest

# Global variables for AWS configuration
AWS_REGIONS = {
    "china": "cn-north-1",
    "us": "us-east-1",
}

AWS_PARTITIONS = {
    "china": "aws-cn",
    "us": "aws",
}


@pytest.fixture(scope="session")
def aws_settings():
    """Provide AWS settings for the current test environment."""
    # You could determine this from environment or other factors
    environment = "china"

    return {"region": AWS_REGIONS[environment], "partition": AWS_PARTITIONS[environment]}

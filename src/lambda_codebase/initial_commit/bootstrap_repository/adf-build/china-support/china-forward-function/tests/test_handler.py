"""
Tests for the AWS Lambda handler that forwards events to Step Functions.
"""
import os
import importlib
from unittest.mock import patch, MagicMock

import pytest
import handler

# pylint: disable=redefined-outer-name,no-member,unused-argument


@pytest.fixture
def mock_env_variables(aws_settings):
    """
    Fixture to mock the SFN_ARN constant in the handler module.
    """
    region = aws_settings["region"]
    partition = aws_settings["partition"]
    sfn_arn = f"arn:{partition}:states:{region}:123456789012:stateMachine:test-sfn"
    with patch.object(handler, "SFN_ARN", sfn_arn):
        yield sfn_arn


@pytest.fixture
def mock_boto3_session():
    """
    Fixture to mock boto3.session.Session and provide access to the mock session object.
    """
    # Create a mock session
    mock_session = MagicMock()

    # Create a mock client that the session will return
    mock_client = MagicMock()

    # Configure the session to return our mock client when requested
    mock_session.client.return_value = mock_client

    # Create a mock for the Session constructor
    mock_session_constructor = MagicMock(return_value=mock_session)

    # Patch boto3.session.Session to use our mock constructor
    with patch("boto3.session.Session", mock_session_constructor):
        # Yield both the session constructor and client mocks
        yield {
            "session_constructor": mock_session_constructor,
            "session": mock_session,
            "client": mock_client
        }


@pytest.fixture
def mock_stepfunction():
    """
    Fixture to mock the Stepfunction class in the handler module.
    """
    mock_sfn = MagicMock()
    mock_sfn.invoke_sfn_execution.return_value = ({"executionArn": "test-arn"}, "test-state-name")
    with patch("handler.Stepfunction", return_value=mock_sfn):
        yield mock_sfn


class TestLambdaHandler:
    """Tests for the lambda_handler function."""

    def test_lambda_handler_with_organizations_event(
        self, mock_env_variables, mock_boto3_session, mock_stepfunction, aws_settings
    ):
        """Test handling of an AWS Organizations event."""
        region = aws_settings["region"]
        partition = aws_settings["partition"]

        event = {
            "source": "aws.organizations",
            "detail-type": "AWS API Call via CloudTrail",
            "detail": {"eventName": "CreateAccount"},
        }

        handler.lambda_handler(event, {})

        # Check that boto3 session was created with correct region
        mock_boto3_session["session_constructor"].assert_called_with(region_name=region)

        # Check that Stepfunction was instantiated correctly
        handler.Stepfunction.assert_called_once()

        # Check that invoke_sfn_execution was called with correct parameters
        expected_arn = f"arn:{partition}:states:{region}:123456789012:stateMachine:test-sfn"
        mock_stepfunction.invoke_sfn_execution.assert_called_once_with(
            sfn_arn=expected_arn,
            input_data=event
        )

    def test_lambda_handler_with_non_organizations_event(
        self, mock_env_variables, mock_boto3_session, mock_stepfunction
    ):
        """Test handling of a non-AWS Organizations event."""
        event = {"source": "aws.ec2", "detail-type": "EC2 Instance State-change Notification"}

        handler.lambda_handler(event, {})

        # Check that Stepfunction was not instantiated
        handler.Stepfunction.assert_not_called()
        mock_stepfunction.invoke_sfn_execution.assert_not_called()

    def test_lambda_handler_with_missing_source(
        self,
        mock_env_variables,
        mock_boto3_session,
        mock_stepfunction
    ):
        """Test handling of an event missing the source field."""
        event = {"detail-type": "Some Event", "detail": {}}

        handler.lambda_handler(event, {})

        # Check that Stepfunction was not instantiated
        handler.Stepfunction.assert_not_called()
        mock_stepfunction.invoke_sfn_execution.assert_not_called()


def test_sfn_name_extraction(aws_settings):
    """Test extraction of Step Function name from ARN."""
    sfn_name = "test-sfn"
    region = aws_settings["region"]
    partition = aws_settings["partition"]
    sfn_arn = f"arn:{partition}:states:{region}:123456789012:stateMachine:{sfn_name}"
    with patch.dict(os.environ, {"SFN_ARN": sfn_arn}):
        importlib.reload(handler)
        assert handler.sfn_name == sfn_name

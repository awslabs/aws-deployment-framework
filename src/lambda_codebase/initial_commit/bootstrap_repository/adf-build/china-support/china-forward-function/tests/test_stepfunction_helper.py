"""
test for stepfunction
"""
import json
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from stepfunction_helper import Stepfunction, convert_decimals


class TestConvertDecimals:
    def test_convert_decimal_to_string(self):
        assert convert_decimals(Decimal("10.5")) == "10.5"

    def test_convert_list_of_decimals(self):
        result = convert_decimals([Decimal("10.5"), Decimal("20.7")])
        assert result == ["10.5", "20.7"]

    def test_convert_dict_with_decimals(self):
        data = {"price": Decimal("10.5"), "quantity": Decimal("2")}
        result = convert_decimals(data)
        assert result == {"price": "10.5", "quantity": "2"}

    def test_convert_nested_structure(self):
        data = {
            "items": [
                {"price": Decimal("10.5"), "quantity": 2},
                {"price": Decimal("20.7"), "quantity": 1}
            ],
            "total": Decimal("41.7"),
        }
        result = convert_decimals(data)
        expected = {
            "items": [
                {"price": "10.5", "quantity": 2},
                {"price": "20.7", "quantity": 1}
            ],
            "total": "41.7"
        }
        assert result == expected

    def test_non_decimal_values_unchanged(self):
        data = {
            "name": "Test",
            "active": True,
            "count": 5,
            "items": ["a", "b", "c"]
            }
        assert convert_decimals(data) == data


class TestStepfunction:
    @pytest.fixture
    def mock_session(self):
        session = MagicMock()
        mock_client = MagicMock()
        session.client.return_value = mock_client
        return session, mock_client

    @pytest.fixture
    def stepfunction(self, mock_session):
        session, _ = mock_session
        logger = MagicMock()
        return Stepfunction(session, logger)

    def test_get_stepfunction_client(self, stepfunction, mock_session):
        session, _ = mock_session
        stepfunction.get_stepfunction_client()
        session.client.assert_called_once_with("stepfunctions")

    def test_invoke_sfn_execution_with_default_name(self, stepfunction, mock_session, aws_settings):
        region = aws_settings["region"]
        partition = aws_settings["partition"]
        _, mock_client = mock_session
        execution_arn = (
            f"arn:{partition}:states:{region}:"
            f"123456789012:execution:test-sfn:test-execution"
        )
        mock_response = {
            "executionArn": execution_arn
        }
        mock_client.start_execution.return_value = mock_response

        with patch("uuid.uuid4", return_value="mocked-uuid"):
            response, name = stepfunction.invoke_sfn_execution(
                sfn_arn=f"arn:{partition}:states:{region}:123456789012:stateMachine:test-sfn",
                input_data={"key": "value"},
            )

        assert response == mock_response
        assert name == "mocked-uuid"
        mock_client.start_execution.assert_called_once()

    def test_invoke_sfn_execution_with_custom_name(self, stepfunction, mock_session, aws_settings):
        region = aws_settings["region"]
        partition = aws_settings["partition"]
        _, mock_client = mock_session
        mock_response = {
            "executionArn": (
                f"arn:{partition}:states:{region}:"
                f"123456789012:execution:test-sfn:custom-name"
            )
        }
        mock_client.start_execution.return_value = mock_response

        response, name = stepfunction.invoke_sfn_execution(
            sfn_arn=f"arn:{partition}:states:{region}:123456789012:stateMachine:test-sfn",
            input_data={"key": "value"},
            execution_name="custom-name",
        )

        assert response == mock_response
        assert name == "custom-name"
        mock_client.start_execution.assert_called_once()

    def test_invoke_sfn_execution_with_decimal_data(self, stepfunction, mock_session, aws_settings):
        region = aws_settings["region"]
        partition = aws_settings["partition"]
        _, mock_client = mock_session
        mock_response = {
            "executionArn": (
                f"arn:{partition}:states:{region}:"
                f"123456789012:execution:test-sfn:test-execution"
            )
        }
        mock_client.start_execution.return_value = mock_response

        input_data = {"amount": Decimal("123.45")}
        expected_input = json.dumps({"amount": "123.45"}, indent=2)

        with patch("uuid.uuid4", return_value="mocked-uuid"):
            stepfunction.invoke_sfn_execution(
                sfn_arn=f"arn:{partition}:states:{region}:123456789012:stateMachine:test-sfn",
                input_data=input_data
            )

        mock_client.start_execution.assert_called_once_with(
            stateMachineArn=f"arn:{partition}:states:{region}:123456789012:stateMachine:test-sfn",
            name="mocked-uuid",
            input=expected_input,
        )

    def test_invoke_sfn_execution_exception(self, stepfunction, mock_session, aws_settings):
        region = aws_settings["region"]
        partition = aws_settings["partition"]
        _, mock_client = mock_session
        mock_client.start_execution.side_effect = Exception("Test exception")

        with pytest.raises(Exception) as excinfo:
            stepfunction.invoke_sfn_execution(
                sfn_arn=f"arn:{partition}:states:{region}:123456789012:stateMachine:test-sfn",
                input_data={"key": "value"},
            )

        assert "Test exception" in str(excinfo.value)
        stepfunction.logger.error.assert_called_once()

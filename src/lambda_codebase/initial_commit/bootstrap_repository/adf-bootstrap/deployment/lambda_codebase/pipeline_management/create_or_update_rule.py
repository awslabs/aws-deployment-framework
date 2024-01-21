"""
Pipeline Management Lambda Function
Creates or Updates an Event Rule for forwarding events
If the source account != the Deployment account
"""

import os
import boto3

from cache import Cache
from rule import Rule
from logger import configure_logger
from cloudwatch import ADFMetrics
from errors import ParameterNotFoundError
from parameter_store import ParameterStore

LOGGER = configure_logger(__name__)
DEPLOYMENT_ACCOUNT_ID = os.environ["ACCOUNT_ID"]
DEPLOYMENT_ACCOUNT_REGION = os.environ["AWS_REGION"]
CLOUDWATCH = boto3.client("cloudwatch")
METRICS = ADFMetrics(CLOUDWATCH, "PIPELINE_MANAGEMENT/RULE")

_CACHE = None


def lambda_handler(event, _):
    """
    Main Lambda Entry point, creating the cross-account EventBridge rule
    if the source account of the CodeCommit repository is in another account
    than the deployment account.

    Such that a change in the source repository will trigger the pipeline.

    Args:
        event (dict): The ADF Pipeline Management State Machine execution
            input object.
    """

    # pylint: disable=W0603
    # Global variable here to cache across lambda execution runtimes.
    global _CACHE
    if not _CACHE:
        _CACHE = Cache()
        METRICS.put_metric_data(
            {"MetricName": "CacheInitialized", "Value": 1, "Unit": "Count"}
        )

    LOGGER.info(event)

    pipeline = event['pipeline_definition']

    source_provider = (
        pipeline.get("default_providers", {})
        .get("source", {})
        .get("provider", "codecommit")
    )
    source_account_id = (
        pipeline.get("default_providers", {})
        .get("source", {})
        .get("properties", {})
        .get("account_id")
    )

    # Resolve codecommit source_account_id in case it is not set
    if source_provider == "codecommit" and not source_account_id:
        # Evaluate as follows:
        # If not set, we have to set it with
        #   - default_scm_codecommit_account_id (if exists)
        #   - or ADF_DEPLOYMENT_ACCOUNT_ID
        # If set, we are done anyways
        LOGGER.debug(
            "source_account_id not found in source_props - ADF will set "
            "it from SSM param default_scm_codecommit_account_id.",
        )
        deployment_account_id = DEPLOYMENT_ACCOUNT_ID
        try:
            parameter_store = ParameterStore(DEPLOYMENT_ACCOUNT_REGION, boto3)
            default_scm_codecommit_account_id = parameter_store.fetch_parameter(
                "/adf/scm/default-scm-codecommit-account-id",
            )
        except ParameterNotFoundError:
            default_scm_codecommit_account_id = deployment_account_id
            LOGGER.debug(
                "default_scm_codecommit_account_id not found in SSM - "
                "Fall back to deployment_account_id.",
            )
        source_account_id = default_scm_codecommit_account_id

        # Create the properties object if it does not exist
        if pipeline["default_providers"]["source"].get("properties") is None:
            pipeline["default_providers"]["source"]["properties"] = {}

        pipeline["default_providers"]["source"]["properties"]["account_id"] = (
            source_account_id
        )

    if (
        source_provider == "codecommit"
        and source_account_id
        and int(source_account_id) != int(DEPLOYMENT_ACCOUNT_ID)
        and not _CACHE.exists(source_account_id)
    ):
        LOGGER.info(
            "Source is CodeCommit and the repository is hosted in the %s "
            "account instead of the deployment account (%s). Creating or "
            "updating EventBridge forward rule to forward change events "
            "from the source account to the deployment account in "
            "EventBridge.",
            source_account_id,
            DEPLOYMENT_ACCOUNT_ID,
        )
        rule = Rule(source_account_id)
        rule.create_update()
        _CACHE.add(source_account_id, True)
        METRICS.put_metric_data(
            {"MetricName": "CreateOrUpdate", "Value": 1, "Unit": "Count"}
        )

    return event

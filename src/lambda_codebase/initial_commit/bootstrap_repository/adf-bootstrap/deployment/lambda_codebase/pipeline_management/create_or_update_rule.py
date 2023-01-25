"""
Pipeline Management Lambda Function
Creates or Updates an Event Rule for forwarding events
If the source account != the Deployment account
"""

import os
import json
import boto3

from cache import Cache
from rule import Rule
from logger import configure_logger
from cloudwatch import ADFMetrics
from events import ADFEvents
from aws_xray_sdk.core import patch_all


patch_all()
LOGGER = configure_logger(__name__)
DEPLOYMENT_ACCOUNT_ID = os.environ["ACCOUNT_ID"]
CLOUDWATCH = boto3.client("cloudwatch")
METRICS = ADFMetrics(CLOUDWATCH, "PIPELINE_MANAGEMENT/RULE")
EVENTS = ADFEvents("PipelineManagement")

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

    pipeline = event["pipeline_definition"]

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
        EVENTS.put_event(
            detail=json.dumps({"source_account_id": source_account_id}),
            detailType="CROSS_ACCOUNT_RULE_CREATED_OR_UPDATED",
            resources=[DEPLOYMENT_ACCOUNT_ID],
        )

    return event

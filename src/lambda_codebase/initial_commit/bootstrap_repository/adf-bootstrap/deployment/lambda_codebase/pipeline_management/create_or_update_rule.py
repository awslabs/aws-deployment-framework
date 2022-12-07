"""
Pipeline Management Lambda Function
Creates or Updates an Event Rule for forwarding events
If the source account != the Deplyment account
"""

import os
import boto3

from cache import Cache
from rule import Rule
from logger import configure_logger
from cloudwatch import ADFMetrics


LOGGER = configure_logger(__name__)
DEPLOYMENT_ACCOUNT_REGION = os.environ["AWS_REGION"]
DEPLOYMENT_ACCOUNT_ID = os.environ["ACCOUNT_ID"]
PIPELINE_MANAGEMENT_STATEMACHINE = os.getenv("PIPELINE_MANAGEMENT_STATEMACHINE_ARN")
CLOUDWATCH = boto3.client("cloudwatch")
METRICS = ADFMetrics(CLOUDWATCH, "PIPELINE_MANAGEMENT/RULE")

_cache = None


def lambda_handler(pipeline, _):
    """Main Lambda Entry point"""

    # pylint: disable=W0603
    # Global variable here to cache across lambda execution runtimes.
    global _cache
    if not _cache:
        _cache = Cache()
        METRICS.put_metric_data(
            {"MetricName": "CacheInitalised", "Value": 1, "Unit": "Count"}
        )

    LOGGER.info(pipeline)

    source_account_id = (
        pipeline.get("default_providers", {})
        .get("source", {})
        .get("properties", {})
        .get("account_id", {})
    )
    if (
        source_account_id
        and int(source_account_id) != int(DEPLOYMENT_ACCOUNT_ID)
        and not _cache.exists(source_account_id)
    ):
        rule = Rule(source_account_id)
        rule.create_update()
        _cache.add(source_account_id, True)
        METRICS.put_metric_data(
            {"MetricName": "CreateOrUpdate", "Value": 1, "Unit": "Count"}
        )

    return pipeline

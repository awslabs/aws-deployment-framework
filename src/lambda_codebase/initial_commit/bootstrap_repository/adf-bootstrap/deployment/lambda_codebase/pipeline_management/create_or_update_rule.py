# Copyright Amazon.com Inc. or its affiliates.
# SPDX-License-Identifier: MIT-0

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

_CACHE_S3 = None
_CACHE_CODECOMMIT = None


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
    global _CACHE_S3, _CACHE_CODECOMMIT

    if not _CACHE_S3:
        _CACHE_S3 = Cache()
        METRICS.put_metric_data(
            {"MetricName": "S3CacheInitialized", "Value": 1, "Unit": "Count"}
        )

    if not _CACHE_CODECOMMIT:
        _CACHE_CODECOMMIT = Cache()
        METRICS.put_metric_data(
            {"MetricName": "CodeCommitCacheInitialized", "Value": 1, "Unit": "Count"}
        )

    LOGGER.info(event)

    pipeline = event['pipeline_definition']

    default_source_provider = pipeline.get("default_providers", {}).get("source", {})
    source_provider = default_source_provider.get("provider", "codecommit")
    source_provider_properties = default_source_provider.get("properties", {})
    source_account_id = source_provider_properties.get("account_id")
    source_bucket_name = source_provider_properties.get("bucket_name")
    if source_provider == "s3":
        if not source_account_id:
            source_account_id = DEPLOYMENT_ACCOUNT_ID
            pipeline["default_providers"]["source"].setdefault("properties", {})["account_id"] = source_account_id
        if not source_bucket_name:
            try:
                parameter_store = ParameterStore(DEPLOYMENT_ACCOUNT_REGION, boto3)
                default_s3_source_bucket_name = parameter_store.fetch_parameter(
                    "/adf/scm/default-s3-source-bucket-name"
                )
            except ParameterNotFoundError:
                default_s3_source_bucket_name = os.environ["S3_BUCKET_NAME"]
                LOGGER.debug("default_s3_source_bucket_name not found in SSM - Fall back to s3_bucket_name.")
            pipeline["default_providers"]["source"].setdefault("properties", {})["bucket_name"] = default_s3_source_bucket_name
            source_bucket_name = default_s3_source_bucket_name
        event_params = {
                "SourceS3BucketName": source_bucket_name
        }
    else:
        event_params = {}
        

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
                "scm/default_scm_codecommit_account_id",
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
        source_account_id
        and int(source_account_id) != int(DEPLOYMENT_ACCOUNT_ID)
        and (
            (source_provider == "codecommit" and not _CACHE_CODECOMMIT.exists(source_account_id))
            or (source_provider == "s3" and not _CACHE_S3.exists(source_account_id))
        )
    ):
        LOGGER.info(
            "Source is %s and the repository/bucket is hosted in the %s "
            "account instead of the deployment account (%s). Creating or "
            "updating EventBridge forward rule to forward change events "
            "from the source account to the deployment account in "
            "EventBridge.",
            source_provider,
            source_account_id,
            DEPLOYMENT_ACCOUNT_ID,
        )

        rule = Rule(source_account_id, source_provider, event_params)
        rule.create_update()

        if source_provider == "codecommit":
            _CACHE_CODECOMMIT.add(source_account_id, True)
            METRICS.put_metric_data(
                {"MetricName": "CodeCommitCreateOrUpdate", "Value": 1, "Unit": "Count"}
            )
        elif source_provider == "s3":
            _CACHE_S3.add(source_account_id, True)
            METRICS.put_metric_data(
                {"MetricName": "S3CreateOrUpdate", "Value": 1, "Unit": "Count"}
            )

    return event

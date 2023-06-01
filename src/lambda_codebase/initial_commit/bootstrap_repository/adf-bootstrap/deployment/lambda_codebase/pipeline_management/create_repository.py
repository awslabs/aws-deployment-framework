"""
Pipeline Management Lambda Function
Creates or Updates a CodeCommit Repository
"""

import os
import json
import boto3
from repo import Repo

from logger import configure_logger
from cloudwatch import ADFMetrics
from parameter_store import ParameterStore
from events import ADFEvents
from aws_xray_sdk.core import patch_all


CLOUDWATCH = boto3.client("cloudwatch")
METRICS = ADFMetrics(CLOUDWATCH, "PIPELINE_MANAGEMENT/REPO")
LOGGER = configure_logger(__name__)
DEPLOYMENT_ACCOUNT_REGION = os.environ["AWS_REGION"]
DEPLOYMENT_ACCOUNT_ID = os.environ["ACCOUNT_ID"]
EVENTS = ADFEvents("PipelineManagement")
patch_all()


def lambda_handler(event, _):
    """
    Main Lambda Entry point, responsible for creating the CodeCommit
    repository if required.

    Args:
        event (dict): The ADF Pipeline Management Input event, holding the
            pipeline definition and event source details.

    Returns:
        dict: The input event.
    """
    pipeline = event.get("pipeline_definition")
    source_provider = (
        pipeline.get("default_providers", {})
        .get("source", {})
        .get("provider", "codecommit")
    )
    if source_provider != "codecommit":
        LOGGER.debug(
            "This pipeline is not a CodeCommit source provider. " "No actions required."
        )
        return event

    parameter_store = ParameterStore(DEPLOYMENT_ACCOUNT_REGION, boto3)
    auto_create_repositories = parameter_store.fetch_parameter(
        "auto_create_repositories"
    )
    LOGGER.info(auto_create_repositories)
    if auto_create_repositories == "enabled":
        code_account_id = (
            pipeline.get("default_providers", {})
            .get("source", {})
            .get("properties", {})
            .get("account_id", {})
        )
        has_custom_repo = (
            pipeline.get("default_providers", {})
            .get("source", {})
            .get("properties", {})
            .get("repository", {})
        )
        if (
            auto_create_repositories
            and code_account_id
            and str(code_account_id).isdigit()
            and not has_custom_repo
        ):
            repo = Repo(
                code_account_id,
                pipeline.get("name"),
                pipeline.get("description"),
            )
            repo.create_update()
            METRICS.put_metric_data(
                {
                    "MetricName": "CreateOrUpdate",
                    "Value": 1,
                    "Unit": "Count",
                }
            )
            EVENTS.put_event(
                detail=json.dumps(
                    {
                        "repository_account_id": code_account_id,
                        "stack_name": repo.stack_name,
                    }
                ),
                detailType="REPOSITORY_CREATED_OR_UPDATED",
                resources=[f'{code_account_id}:{pipeline.get("name")}'],
            )

    code_account_id = (
        pipeline.get("default_providers", {})
        .get("source", {})
        .get("properties", {})
        .get("account_id")
    )
    has_custom_repo = (
        pipeline.get("default_providers", {})
        .get("source", {})
        .get("properties", {})
        .get("repository", {})
    )
    if code_account_id and str(code_account_id).isdigit() and not has_custom_repo:
        repo = Repo(
            code_account_id,
            pipeline.get("name"),
            pipeline.get("description"),
        )
        repo.create_update()
        METRICS.put_metric_data(
            {
                "MetricName": "CreateOrUpdate",
                "Value": 1,
                "Unit": "Count",
            }
        )

    return event

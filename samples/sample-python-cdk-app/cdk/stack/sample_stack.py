# Copyright Amazon.com Inc. or its affiliates.
# SPDX-License-Identifier: Apache-2.0

from aws_cdk import (
    CfnOutput,
    CfnParameter,
    Duration,
    Stack,
    aws_lambda,
    aws_s3 as s3,
)
from constructs import Construct


class SampleStack(Stack):
    """A minimal stack that deploys a single "Hello World" Lambda function.

    The Lambda's deployment package is NOT bundled by CDK. Instead it is built
    and zipped in buildspec.yml (inside its own venv) and uploaded to the ADF
    cross-region asset S3 bucket by ADF's ``upload:`` parameter resolver. This
    stack receives the bucket name and object key as CloudFormation parameters
    (wired up in ``params/*.yml``) and loads the code from there. This keeps the
    synthesized template asset-free so ADF can deploy it via a plain
    CloudFormation action, without needing CDK bootstrap in the target accounts.
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # --- Asset location, provided by ADF via params/*.yml -----------------
        asset_bucket_name_param = CfnParameter(
            self,
            "AssetBucketParam",
            type="String",
            description="Name of the ADF S3 Asset bucket holding the Lambda code asset.",
            min_length=1,
        )
        asset_bucket_name_param.override_logical_id("AssetBucketParam")

        lambda_asset_object_key_param = CfnParameter(
            self,
            "LambdaAssetObjectKeyParam",
            type="String",
            description="S3 object key of the zipped Lambda code asset.",
            min_length=1,
        )
        lambda_asset_object_key_param.override_logical_id(
            "LambdaAssetObjectKeyParam",
        )

        asset_bucket = s3.Bucket.from_bucket_name(
            self,
            "AssetBucket",
            bucket_name=asset_bucket_name_param.value_as_string,
        )

        # --- Hello World Lambda ----------------------------------------------
        function = aws_lambda.Function(
            self,
            "SampleFunction",
            runtime=aws_lambda.Runtime.PYTHON_3_12,
            architecture=aws_lambda.Architecture.X86_64,
            handler="app.lambda_handler",
            code=aws_lambda.Code.from_bucket(
                asset_bucket,
                lambda_asset_object_key_param.value_as_string,
            ),
            timeout=Duration.seconds(10),
            memory_size=128,
            tracing=aws_lambda.Tracing.ACTIVE,
            environment={
                "POWERTOOLS_SERVICE_NAME": "sample-python-cdk-app",
                "POWERTOOLS_METRICS_NAMESPACE": "sample-python-cdk-app",
                "LOG_LEVEL": "INFO",
            },
        )

        # --- Outputs ----------------------------------------------------------
        CfnOutput(
            self,
            "SampleFunctionName",
            description="Name of the Hello World Lambda function.",
            value=function.function_name,
        )
        CfnOutput(
            self,
            "SampleFunctionArn",
            description="ARN of the Hello World Lambda function.",
            value=function.function_arn,
        )

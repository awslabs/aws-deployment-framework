#!/usr/bin/env python3
# Copyright Amazon.com Inc. or its affiliates.
# SPDX-License-Identifier: Apache-2.0

import aws_cdk as cdk

from stack.sample_stack import SampleStack

app = cdk.App(
    # ADF deploys the *synthesized* template through a CloudFormation action,
    # not via `cdk deploy`. There is therefore no CDK bootstrap stack in the
    # target accounts, so we disable the bootstrap version parameter/rule that
    # CDK would otherwise inject into the template.
    default_stack_synthesizer=cdk.DefaultStackSynthesizer(
        generate_bootstrap_version_rule=False,
    ),
)

SampleStack(app, "sample-python-cdk-app")

app.synth()

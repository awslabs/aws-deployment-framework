#!/usr/bin/env bash

# Copyright Amazon.com Inc. or its affiliates.
# SPDX-License-Identifier: Apache-2.0

set -e

cd src/lambda_vpc

pip install crhelper -t .

cd -

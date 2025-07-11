# Copyright Amazon.com Inc. or its affiliates.
# SPDX-License-Identifier: Apache-2.0

data "aws_partition" "current" {}

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~= 6.3"
    }
  }
  required_version = ">= 0.13.0"
}
provider "aws" {
  assume_role {
    role_arn = "arn:${data.aws_partition.current}:iam::${var.TARGET_ACCOUNT_ID}:role/${var.TARGET_ACCOUNT_ROLE}"
  }
}

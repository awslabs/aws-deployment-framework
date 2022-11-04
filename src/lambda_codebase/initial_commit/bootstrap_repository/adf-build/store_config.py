# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
Store config entry point for storing the adfconfig.yml configuration
into the Parameter Store such that the bootstrapping and account management
steps can execute correctly when triggered.

This gets executed from within AWS CodeBuild in the management account.
"""
import os
from config import Config
from logger import configure_logger

ADF_VERSION = os.environ["ADF_VERSION"]
ADF_LOG_LEVEL = os.environ["ADF_LOG_LEVEL"]
LOGGER = configure_logger(__name__)


def main():
    """
    Main entry point to store the configuration into AWS Systems
    Manager Parameter Store
    """
    LOGGER.info("ADF Version %s", ADF_VERSION)
    LOGGER.info("ADF Log Level is %s", ADF_LOG_LEVEL)

    LOGGER.info(
        "Storing configuration values in AWS Systems Manager Parameter Store."
    )
    config = Config()
    config.store_config()
    LOGGER.info("Configuration values stored successfully.")


if __name__ == '__main__':
    main()

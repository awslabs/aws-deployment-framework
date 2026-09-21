# Copyright Amazon.com Inc. or its affiliates.
# SPDX-License-Identifier: MIT-0

"""
__init__ for terraform tests module.

Adds the `helpers/terraform` directory to the path so that the
`get_accounts` module under test can be imported directly.
"""

import sys
import os

sys.path.append(
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..', '..', 'terraform')
    )
)

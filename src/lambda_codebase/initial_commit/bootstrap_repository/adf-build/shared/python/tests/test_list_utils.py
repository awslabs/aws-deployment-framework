# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

# pylint: skip-file

from ..list_utils import flatten_to_unique_sorted


def test_flatten_to_unique_sorted():
    """
    Flatten and sort the list
    """
    result = flatten_to_unique_sorted(
        [
            # Nested lists:
            ['val9', 'val0', 'val1'],
            ['val1', 'val2'],
            # Empty list
            [],
            # Double nested list:
            [
                ['val8', 'val2'],
                'val4',
            ],
            # Single item
            'val3',
        ],
    )
    assert result == ['val0', 'val1', 'val2', 'val3', 'val4', 'val8', 'val9']

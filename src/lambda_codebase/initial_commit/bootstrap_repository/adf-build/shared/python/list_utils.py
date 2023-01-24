# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
List utilities to ease list management.
"""


def _flatten_list(input_list):
    result = []
    for item in input_list:
        if isinstance(item, list):
            if len(item) > 0:
                result.extend(
                    _flatten_list(item),
                )
        else:
            result.append(item)
    return result


def flatten_to_unique_sorted(input_list):
    """
    Flatten nested lists and return a unique and sorted list of items.
    This will recursively iterate over the lists and flatten them together
    into one list. It will then remove redundant items, followed by sorting
    them.

    Args:
        input_list (list): The input list that could hold multiple levels of
            nested lists.

    Returns:
        List with unique and sorted list of items.
    """
    result = _flatten_list(input_list)
    return sorted(list(set(result)))

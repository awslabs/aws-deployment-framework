# Copyright Amazon.com Inc. or its affiliates.
# SPDX-License-Identifier: MIT-0

"""
Used as a cache for AWS Organizations calls within threads.
A single instance of this class is passed into all threads to act
as a cache
"""


class Cache:
    def __init__(self):
        self._stash = {}

    def exists(self, key):
        return key in self._stash

    def get(self, key):
        try:
            return self._stash[key]
        except KeyError:
            return None

    def add(self, key, value):
        self._stash[key] = value

    def remove(self, key):
        if not self.exists(key):
            return
        del self._stash[key]

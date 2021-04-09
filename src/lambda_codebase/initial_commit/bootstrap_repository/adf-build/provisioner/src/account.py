# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""
Model for handling AWS accounts within the organization. The Account class
allows you to create or update a new account.
"""


class Account:
    def __init__(
            self,
            full_name,
            email,
            ou_path,
            alias=None,
            delete_default_vpc=False,
            allow_direct_move_between_ou=False,
            allow_billing=True,
            support_level='basic',
            tags=None
    ):
        self.full_name = full_name
        self.email = email
        self.ou_path = ou_path
        self.delete_default_vpc = delete_default_vpc
        self.allow_direct_move_between_ou = allow_direct_move_between_ou
        self.allow_billing = allow_billing
        self.alias = alias
        self.support_level = support_level

        if tags is None:
            self.tags = {}
        else:
            self.tags = tags

    @classmethod
    def load_from_config(cls, config):
        """Initialize Account class from configuration object"""
        return cls(
            config["account_full_name"],
            config["email"],
            config["organizational_unit_path"],
            alias=config.get(
                "alias",
                None),
            delete_default_vpc=config.get(
                "delete_default_vpc",
                False),
            allow_direct_move_between_ou=config.get(
                "allow_direct_move_between_ou",
                False),
            allow_billing=config.get(
                "allow_billing",
                True),
            support_level=config.get(
                "support_level",
                'basic'),
            tags=config.get(
                "tags",
                {}))

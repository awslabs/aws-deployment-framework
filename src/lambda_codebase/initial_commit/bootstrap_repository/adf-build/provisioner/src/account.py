"""
# account.py
Model for handling AWS accounts within the organization. The Account class
allows you to create or update a new account.
"""

from time import sleep

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
            tags=None
    ):
        """Initialize Account object.

        :param full_name: Full name of the account
        :param email: Valid email address of account
        :param ou_path: Organizational Unit path. For nested OUs use / notation, eg. us/development.
                        Use root identifier to target root OU (eg. r-abc1) or just use '/'

        :param alias: Optional Alias to use, if None the alias will default to full_name
        :param delete_default_vpc: Set this to True to delete the default vpc from the account
        :param allow_direct_move_between_ou: Set this to False to prevent the script from moving
                                             an account directly from one OU to another. This is
                                             useful if you are using the AWS Deployment Framework
                                             as it requires you to first move an account to the root
                                             to trigger the base cloudformation stack updates.
        :param allow_billing: Set this to False to prevent account admins from using the billing console
        :param tags: a dict containing optional tags for the account
        """
        self.full_name = full_name
        self.email = email
        self.ou_path = ou_path
        self.delete_default_vpc = delete_default_vpc
        self.allow_direct_move_between_ou = allow_direct_move_between_ou
        self.allow_billing = allow_billing

        if alias is None:
            self.alias = full_name
        else:
            self.alias = alias

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
            alias=config.get("alias", None),
            delete_default_vpc=config.get("delete_default_vpc", False),
            allow_direct_move_between_ou=config.get("allow_direct_move_between_ou", False),
            allow_billing=config.get("allow_billing", True),
            tags=config.get("tags", {})
        )

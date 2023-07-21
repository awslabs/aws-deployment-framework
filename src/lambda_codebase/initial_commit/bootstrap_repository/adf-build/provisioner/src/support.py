"""Support module used throughout the ADF
"""
from enum import Enum
from botocore.config import Config
from botocore.exceptions import ClientError, BotoCoreError
from logger import configure_logger
from .account import Account


LOGGER = configure_logger(__name__)


class SupportLevel(Enum):
    BASIC = "basic"
    DEVELOPER = "developer"
    BUSINESS = "business"
    ENTERPRISE = "enterprise"


class Support:  # pylint: disable=R0904
    """
    Class used for accessing AWS Support API
    """
    _config = Config(
        retries={
            "max_attempts": 30,
        },
    )

    def __init__(self, role):
        self.client = role.client(
            "support",
            region_name='us-east-1',
            config=Support._config,
        )

    def get_support_level(self) -> SupportLevel:
        """
        Gets the AWS Support Level of the current Account
        based on the Role passed in during the init of the Support class.

        :returns:
            SupportLevels Enum defining the level of AWS support.

        :raises:
            ClientError
            BotoCoreError

        """
        try:
            severity_levels = (
                self.client.describe_severity_levels()['severityLevels']
            )
            available_support_codes = [
                level['code'] for level in severity_levels
            ]

            # See: https://aws.amazon.com/premiumsupport/plans/ for insights
            # into the interpretation of the available support codes.

            if 'critical' in available_support_codes:
                # Business Critical System Down Severity
                return SupportLevel.ENTERPRISE
            if 'urgent' in available_support_codes:
                # Production System Down Severity
                return SupportLevel.BUSINESS
            if 'low' in available_support_codes:
                # System Impaired Severity
                return SupportLevel.DEVELOPER

            return SupportLevel.BASIC

        except (ClientError, BotoCoreError) as e:
            if e.response["Error"]["Code"] == "SubscriptionRequiredException":
                LOGGER.info('Enterprise Support is not enabled')
                return SupportLevel.BASIC
            raise

    def set_support_level_for_account(
        self,
        account: Account,
        account_id: str,
        current_level: SupportLevel = SupportLevel.BASIC,
    ):
        """
        Sets the support level for the account. If the current_value is the same
        as the value in the instance of the account Class it will not create a
        new ticket.

        Currently only supports "basic|enterprise" tiers.

        :param account:  Instance of Account class
        :param account_id: AWS Account ID of the account that will have support
            configured for it.
        :param current_level: SupportLevel value that represents the current
            support tier of the account (Default: Basic)
        :return: Void
        :raises: ValueError if account.support_level is not a valid/supported
            SupportLevel.
        """
        desired_level = SupportLevel(account.support_level)

        if desired_level is current_level:
            LOGGER.info(
                'Account %s (%s) already has %s support enabled.',
                account.full_name,
                account_id,
                desired_level.value,
            )

        elif desired_level is SupportLevel.ENTERPRISE:
            LOGGER.info(
                'Enabling %s for Account %s (%s)',
                desired_level.value,
                account.full_name,
                account_id,
            )
            self._enable_support_for_account(account, account_id, desired_level)

        else:
            LOGGER.error(
                'Invalid support tier configured: %s. '
                'Currently only "%s" or "%s" are accepted.',
                desired_level.value,
                SupportLevel.BASIC.value,
                SupportLevel.ENTERPRISE.value,
                exc_info=True,
            )
            raise ValueError(
                f'Invalid Support Tier Value: {desired_level.value}'
            )

    def _enable_support_for_account(
        self,
        account: Account,
        account_id,
        desired_level: SupportLevel,
    ):
        """
        Raises a support ticket in the organization root account, enabling]
        support for the account specified by account_id.

        :param account: Instance of Account class
        :param account_id: AWS Account ID, of the account that will have
            support configured
        :param desired_level: Desired Support Level

        :return: Void

        :raises: ClientError, BotoCoreError.
        """
        try:
            cc_email = account.email
            subject = (
                f'[ADF] Enable {desired_level.value} Support for '
                f'account: {account_id}'
            )
            body = (
                f'Hello, \n'
                f'Can {desired_level.value} support be enabled on '
                f'Account: {account_id} ({account.email}) \n'
                'Thank you!\n'
                '(This ticket was raised automatically via ADF)'

            )
            LOGGER.info(
                'Creating AWS Support ticket. %s Support for Account %s (%s)',
                desired_level.value,
                account.full_name,
                account_id,
            )

            response = self.client.create_case(
                subject=subject,
                serviceCode='account-management',
                severityCode='low',
                categoryCode='billing',
                communicationBody=body,
                ccEmailAddresses=[
                    cc_email,
                ],
                language='en',
            )

            LOGGER.info(
                'AWS Support ticket: %s has been created. %s Support has '
                'been requested on Account %s (%s). %s has been CCd',
                response["caseId"],
                desired_level.value,
                account.full_name,
                account_id,
                account.email,
            )

        except (ClientError, BotoCoreError):
            LOGGER.error(
                'Failed to enable %s support for account: %s (%s): %s',
                desired_level.value,
                account.full_name,
                account.alias,
                account_id,
                exc_info=True,
            )
            raise

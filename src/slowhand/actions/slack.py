from typing import override

from pydantic import BaseModel, Field
from slack_sdk import WebClient

from slowhand.config import settings
from slowhand.errors import SlowhandException
from slowhand.logging import get_logger

from .base import Action

logger = get_logger(__name__)


class SlackSendMessage(Action):
    name = "slack-send-message"

    class Params(BaseModel):
        channel: str = Field(pattern=r"^#[\w\-]+$")
        message: str

    @override
    def run(self, params, *, context, dry_run):
        # TODO: Need the "Cadence" Slack App to be approved and installed.
        logger.warning(
            "🚧  TODO: Waiting for the Slack App to be approved and installed..."
        )
        logger.warning(
            "🚧  See: https://api.slack.com/apps/A0ABCGHB68G/install-on-team"
        )

        params = self.Params(**params)

        # api_token = settings.slack.api_token
        # if not api_token:
        #     raise SlowhandException("Slack API token is not configured")

        my_member_id = settings.slack.my_member_id
        me = f"<@{my_member_id}>" if my_member_id else "SOMEONE"
        text = params.message.replace("@me", me)

        if not dry_run:
            logger.info(
                "Sending message to Slack channel: %s\n\n%s",
                params.channel,
                text,
            )
            logger.warning("👆  Send the message by yourself.")
            # client = WebClient(token=api_token.get_secret_value())
            # resp = client.chat_postMessage(channel=params.channel, text=text)
            # logger.info("Message sent: %s", resp.status_code)
        else:
            logger.warning(
                "Dry-run: Sending message to Slack channel: %s\n\n%s",
                params.channel,
                text,
            )

    def _run_for_real(self, params, *, context, dry_run):
        params = self.Params(**params)

        api_token = settings.slack.api_token
        if not api_token:
            raise SlowhandException("Slack API token is not configured")

        my_member_id = settings.slack.my_member_id
        me = f"<@{my_member_id}>" if my_member_id else "SOMEONE"
        text = params.message.replace("@me", me)

        if not dry_run:
            logger.info(
                "Sending message to Slack channel: %s\n\n%s",
                params.channel,
                text,
            )
            client = WebClient(token=api_token.get_secret_value())
            resp = client.chat_postMessage(channel=params.channel, text=text)
            logger.info("Message sent: %s", resp.status_code)
        else:
            logger.warning(
                "Dry-run: Sending message to Slack channel: %s\n\n%s",
                params.channel,
                text,
            )

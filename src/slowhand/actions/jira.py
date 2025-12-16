from textwrap import dedent
from typing import Any, override

from jira import JIRA
from pydantic import BaseModel, Field

from slowhand.config import settings
from slowhand.errors import SlowhandException
from slowhand.logging import get_logger

from .base import Action

logger = get_logger(__name__)


# Main
_COMPONENT_VERSION = "customfield_10312"
_BUSINESS_JUSTIFICATION = "customfield_10128"
_ROLLBACK_PROCEDURE = "customfield_10136"
_VAULT_CONFIGURATION_ITEM = "customfield_10507"
_VAULT_CONFIGURATION_ITEM_CHANGE_TYPE = "customfield_10508"
_VAULT_ENVIRONMENT = "customfield_10509"
_IS_THIS_A_PRODUCTION_HOTFIX = "customfield_10574"
_IS_MANDATORY_QA_TESTING_REQUIRED_ON_PPR1 = "customfield_11492"

# QA status
_WAS_THIS_CHANGE_TESTED = "customfield_10510"
_QA_DESCRIPTION = "customfield_10511"

# Risk analysis
_RISK_OF_THE_CHANGE = "customfield_10132"
_DETAILS_OF_THE_RISK = "customfield_10133"


def _to_value(value: str, *, child: dict[str, str] | None = None) -> dict[str, Any]:
    return {"value": value} | ({"child": child} if child else {})


class JiraCreateMoTicketParams(BaseModel):
    component: str
    version: str
    pr_link: str = Field(alias="pr-link", pattern=r"^https://github\.com/.+$")


class JiraCreateMoTicket(Action):
    """
    See an example MO ticket: https://ledgerhq.atlassian.net/browse/MO-12335
    """

    name = "jira-create-mo-ticket"

    @override
    def run(self, params, *, context):
        params = JiraCreateMoTicketParams(**params)

        jira_server = settings.jira.server
        jira_email = settings.jira.email
        jira_api_token = settings.jira.api_token
        if jira_server or not jira_email or not jira_api_token:
            raise SlowhandException("JIRA server, email or API token is not configured")

        jira = JIRA(
            server=jira_server,
            basic_auth=(jira_email, jira_api_token.get_secret_value()),
        )

        component_version = f"{params.component}-{params.version}"
        ticket_fields = {
            "project": {"key": "MO"},
            "summary": f"[prd][{params.component}] Deploy {component_version}",
            "description": dedent(
                f"""
                Hello dear MS team,

                Please review and merge the following PR to deploy {component_version} to prd:

                {params.pr_link}

                Thanks in advance!
                """
            ),
            "issuetype": {"name": "Vault Standard Change"},
            "priority": {"name": "Medium"},
            # Custom fields (replace customfield_xxxxx with your actual field IDs)
            # These IDs must be checked in your Jira instance
            _COMPONENT_VERSION: component_version,
            _BUSINESS_JUSTIFICATION: "To bring new features",
            _RISK_OF_THE_CHANGE: _to_value("Low"),
            _DETAILS_OF_THE_RISK: "No risk expected",
            _ROLLBACK_PROCEDURE: "rollback the merge",
            _VAULT_CONFIGURATION_ITEM: _to_value("Other: to be specified"),
            _VAULT_CONFIGURATION_ITEM_CHANGE_TYPE: [_to_value("Version Change")],
            _VAULT_ENVIRONMENT: [_to_value("Production")],
            _WAS_THIS_CHANGE_TESTED: _to_value(
                "Yes.",
                child=_to_value("I will provide testing evidence in the ticket"),
            ),
            _QA_DESCRIPTION: "We have nightly tests running on main & stg, and duly tested the migration on both ppr2 and ppr.",
            _IS_THIS_A_PRODUCTION_HOTFIX: _to_value("No, this is regular change."),
            _IS_MANDATORY_QA_TESTING_REQUIRED_ON_PPR1: {
                "value": "Yes. (please specify QA person in Jira comment)"
            },
        }

        logger.info("Creating MO ticket to deploy: %s", component_version)
        mo_ticket = jira.create_issue(fields=ticket_fields)
        logger.info("MO ticket created: %s", mo_ticket.key)

        return {
            "issue_key": mo_ticket.key,
            "issue_link": f"{jira_server}/browse/{mo_ticket.key}",
        }

from __future__ import annotations

import logging
from functools import cached_property
from typing import Any

from jira import JIRA
from jira.exceptions import JIRAError

from .config import get_jira_settings, JiraSettings
from .exceptions import JiraIntegrationError

logger = logging.getLogger(__name__)


class JiraClient:
    """
    Thin, opinionated wrapper around the official `jira` package.

    Handles all authentication and server configuration so you don't have to.
    """

    def __init__(self, settings: JiraSettings | None = None):
        self.settings = settings or get_jira_settings()
        self._jira: JIRA | None = None

    @cached_property
    def jira(self) -> JIRA:
        """Lazy-initialized underlying JIRA client."""
        options: dict[str, Any] = {
            "server": self.settings.server,
            "verify": self.settings.verify_ssl,
        }
        if self.settings.proxies:
            options["proxies"] = self.settings.proxies

        try:
            if self.settings.token_auth:
                # Jira Server / Data Center
                client = JIRA(options=options, token_auth=self.settings.token_auth)
            elif self.settings.email and self.settings.api_token:
                # Jira Cloud
                client = JIRA(
                    options=options,
                    basic_auth=(self.settings.email, self.settings.api_token),
                )
            else:
                raise JiraIntegrationError(
                    "No valid authentication configured. "
                    "Set either JIRA_TOKEN_AUTH or (JIRA_EMAIL + JIRA_API_TOKEN)."
                )

            logger.info("Connected to Jira at %s", self.settings.server)
            return client

        except JIRAError as e:
            logger.error("Jira connection failed: %s", e)
            raise JiraIntegrationError(f"Failed to connect to Jira: {e}") from e

    def __getattr__(self, name: str) -> Any:
        """Delegate all unknown attributes/methods to the underlying JIRA client."""
        return getattr(self.jira, name)

    def create_issue_simple(
        self, project: str, summary: str, description: str = "", **fields: Any
    ) -> Any:
        """Convenience method for quick issue creation."""
        issue_dict = {
            "project": {"key": project},
            "summary": summary,
            "description": description,
            "issuetype": {"name": "Task"},
            **fields,
        }
        return self.jira.create_issue(fields=issue_dict)

    def close(self) -> None:
        if self._jira:
            self._jira.close()
            self._jira = None


# Singleton-style factory for convenience
_jira_client: JiraClient | None = None


def get_jira_client() -> JiraClient:
    """Returns a cached JiraClient instance."""
    global _jira_client
    if _jira_client is None:
        _jira_client = JiraClient()
    return _jira_client
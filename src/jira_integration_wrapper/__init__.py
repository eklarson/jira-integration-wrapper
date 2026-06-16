from importlib.metadata import PackageNotFoundError, version

from .client import JiraClient, get_jira_client, reset_jira_client
from .config import JiraSettings, get_jira_settings
from .exceptions import (
    JiraAuthError,
    JiraConfigError,
    JiraConnectionError,
    JiraIntegrationError,
)

try:
    __version__ = version("jira-integration-wrapper")
except PackageNotFoundError:
    __version__ = "0.2.0"

__all__ = [
    "JiraClient",
    "get_jira_client",
    "reset_jira_client",
    "JiraSettings",
    "get_jira_settings",
    "JiraIntegrationError",
    "JiraConfigError",
    "JiraAuthError",
    "JiraConnectionError",
]

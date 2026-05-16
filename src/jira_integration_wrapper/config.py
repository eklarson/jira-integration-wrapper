import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass
class JiraSettings:
    """Configuration for connecting to Jira."""
    server: str
    email: str | None = None          # Jira Cloud
    api_token: str | None = None      # Jira Cloud
    token_auth: str | None = None     # Jira Server/DC PAT
    verify_ssl: bool = True
    proxies: dict | None = None


def get_jira_settings() -> JiraSettings:
    server = os.getenv("JIRA_SERVER")
    if not server:
        raise ValueError(
            "JIRA_SERVER environment variable is required. "
            "See .env.example for setup."
        )

    return JiraSettings(
        server=server,
        email=os.getenv("JIRA_EMAIL"),
        api_token=os.getenv("JIRA_API_TOKEN"),
        token_auth=os.getenv("JIRA_TOKEN_AUTH"),
        verify_ssl=os.getenv("JIRA_VERIFY_SSL", "true").lower() == "true",
    )
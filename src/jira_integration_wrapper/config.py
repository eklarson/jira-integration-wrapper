import json
import logging
import os
from dataclasses import dataclass

from dotenv import load_dotenv

from .exceptions import JiraConfigError

logger = logging.getLogger(__name__)


_dotenv_loaded = False


def _ensure_dotenv_loaded() -> None:
    """Load .env file at most once, only when explicitly requested."""
    global _dotenv_loaded
    if not _dotenv_loaded:
        load_dotenv()
        _dotenv_loaded = True


@dataclass
class JiraSettings:
    """Configuration for connecting to Jira.

    Can be constructed directly (useful for tests and advanced usage)
    or via get_jira_settings() which reads from environment variables.
    """

    server: str
    email: str | None = None  # Jira Cloud
    api_token: str | None = None  # Jira Cloud
    token_auth: str | None = None  # Jira Server/DC PAT
    verify_ssl: bool = True
    proxies: dict[str, str] | None = None

    def has_auth(self) -> bool:
        """Return True if at least one authentication method is configured."""
        return bool(
            self.token_auth or (self.email and self.api_token)
        )


def get_jira_settings(*, load_env: bool = True) -> JiraSettings:
    """Load Jira connection settings from environment variables.

    Args:
        load_env: If True (default), load variables from a .env file using
            python-dotenv before reading os.environ. The .env file is loaded
            at most once per process.

    Environment variables:
        JIRA_SERVER (required)
        JIRA_EMAIL + JIRA_API_TOKEN  (Jira Cloud)
        JIRA_TOKEN_AUTH              (Jira Server / Data Center PAT)
        JIRA_VERIFY_SSL              (default: true)
        JIRA_PROXIES                 (optional JSON object, e.g. '{"https": "..."}')
        JIRA_HTTP_PROXY / JIRA_HTTPS_PROXY (alternative to JIRA_PROXIES)
    """
    if load_env:
        _ensure_dotenv_loaded()

    server = os.getenv("JIRA_SERVER")
    if not server:
        raise JiraConfigError(
            "JIRA_SERVER environment variable is required.\n"
            "Set it in your environment or .env file. "
            "See .env.example for the expected format."
        )

    # Proxies: prefer explicit JSON, fall back to separate HTTP/HTTPS vars
    proxies: dict[str, str] | None = None
    proxies_raw = os.getenv("JIRA_PROXIES")
    if proxies_raw:
        try:
            parsed = json.loads(proxies_raw)
            if isinstance(parsed, dict):
                proxies = {str(k): str(v) for k, v in parsed.items()}
        except (json.JSONDecodeError, TypeError):
            logger.warning(
                "Invalid JIRA_PROXIES JSON; falling back to JIRA_HTTP_PROXY / JIRA_HTTPS_PROXY"
            )

    if proxies is None:
        http_proxy = os.getenv("JIRA_HTTP_PROXY")
        https_proxy = os.getenv("JIRA_HTTPS_PROXY")
        if http_proxy or https_proxy:
            proxies = {}
            if http_proxy:
                proxies["http"] = http_proxy
            if https_proxy:
                proxies["https"] = https_proxy

    settings = JiraSettings(
        server=server,
        email=os.getenv("JIRA_EMAIL"),
        api_token=os.getenv("JIRA_API_TOKEN"),
        token_auth=os.getenv("JIRA_TOKEN_AUTH"),
        verify_ssl=os.getenv("JIRA_VERIFY_SSL", "true").lower() == "true",
        proxies=proxies,
    )

    # Basic validation: at least one auth method should be present.
    # We allow construction of incomplete settings (for tests/advanced use),
    # but fail fast when coming through the normal env path.
    if load_env and not settings.has_auth():
        raise JiraConfigError(
            "No Jira authentication configured.\n"
            "Set either:\n"
            "  - JIRA_EMAIL + JIRA_API_TOKEN (for Jira Cloud), or\n"
            "  - JIRA_TOKEN_AUTH (for Jira Server / Data Center)\n"
            "See .env.example for examples."
        )

    return settings

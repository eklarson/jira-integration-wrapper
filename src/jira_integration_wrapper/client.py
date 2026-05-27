from __future__ import annotations

import logging
import threading
from typing import Any

from jira import JIRA
from jira.exceptions import JIRAError

from .config import get_jira_settings, JiraSettings
from .exceptions import (
    JiraAuthError,
    JiraConnectionError,
)

logger = logging.getLogger(__name__)


class JiraClient:
    """
    Thin, opinionated wrapper around the official `jira` package.

    Handles all authentication and server configuration so you don't have to.

    Most methods are delegated to the underlying JIRA client via __getattr__.
    This means you have access to the full jira library API (search_issues,
    create_issue, transition_issue, etc.).

    Note on delegation:
        Python's __getattr__ does not intercept special "dunder" methods
        (__enter__, __len__, __repr__, etc.). For those, access them via
        the .jira attribute directly: client.jira.<method>.

    Resource management:
        The wrapper holds a network session. Use the context manager form
        when you want explicit cleanup:

            with JiraClient() as client:
                client.search_issues(...)

        Or call .close() manually.
    """

    def __init__(self, settings: JiraSettings | None = None):
        self.settings = settings or get_jira_settings()
        self._jira: JIRA | None = None
        self._lock = threading.Lock()

    @property
    def jira(self) -> JIRA:
        """Lazily-initialized underlying JIRA client.

        The real connection is created on first access and reused.
        After .close(), the next access will create a fresh connection.
        """
        if self._jira is None:
            with self._lock:
                # Double-check inside the lock
                if self._jira is None:
                    self._jira = self._create_jira_client()
        return self._jira

    def _create_jira_client(self) -> JIRA:
        """Create and return a configured JIRA client instance."""
        options: dict[str, Any] = {
            "server": self.settings.server,
            "verify": self.settings.verify_ssl,
        }
        if self.settings.proxies:
            options["proxies"] = self.settings.proxies

        try:
            if self.settings.token_auth:
                # Jira Server / Data Center (Personal Access Token)
                client = JIRA(options=options, token_auth=self.settings.token_auth)
            elif self.settings.email and self.settings.api_token:
                # Jira Cloud
                client = JIRA(
                    options=options,
                    basic_auth=(self.settings.email, self.settings.api_token),
                )
            else:
                # This path is rarely reached because get_jira_settings() now
                # validates early, but we keep a defensive error.
                raise JiraAuthError(
                    "No valid authentication configured. "
                    "Set either JIRA_TOKEN_AUTH or (JIRA_EMAIL + JIRA_API_TOKEN)."
                )

            logger.info("Connected to Jira at %s", self.settings.server)
            return client

        except JIRAError as e:
            logger.error("Jira connection failed: %s", e)
            raise JiraConnectionError(f"Failed to connect to Jira: {e}") from e

    def __getattr__(self, name: str) -> Any:
        """Delegate unknown attributes/methods to the underlying JIRA client.

        Limitation: This does not intercept dunder methods (e.g. __repr__,
        __enter__). Use client.jira.xxx for those cases.
        """
        return getattr(self.jira, name)

    def __dir__(self) -> list[str]:
        """Support tab-completion and dir() by including delegated attributes."""
        base = set(super().__dir__())
        if self._jira is not None:
            try:
                base.update(dir(self._jira))
            except Exception:
                pass
        return sorted(base)

    def __enter__(self) -> JiraClient:
        """Enter the runtime context (supports 'with JiraClient() as client:')."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit the context and close the underlying connection."""
        self.close()

    def __repr__(self) -> str:
        status = "connected" if self._jira is not None else "not connected"
        return f"<JiraClient server={self.settings.server!r} ({status})>"

    def create_issue_simple(
        self,
        project: str,
        summary: str,
        description: str = "",
        issuetype: str = "Task",
        **fields: Any,
    ) -> Any:
        """Convenience method for quick issue creation.

        Args:
            project: Project key (e.g. "PROJ").
            summary: Issue summary/title.
            description: Optional description.
            issuetype: Issue type name (defaults to "Task" for backward compat).
            **fields: Additional fields passed through to the Jira API.
        """
        issue_dict = {
            "project": {"key": project},
            "summary": summary,
            "description": description,
            "issuetype": {"name": issuetype},
            **fields,
        }
        return self.jira.create_issue(fields=issue_dict)

    def close(self) -> None:
        """Close the underlying JIRA session and release resources.

        After calling close(), the next access to any delegated method
        (or .jira) will transparently create a new connection.
        """
        with self._lock:
            if self._jira is not None:
                try:
                    self._jira.close()  # type: ignore[no-untyped-call]
                except Exception:  # pragma: no cover - best effort cleanup
                    logger.debug("Error during Jira session close", exc_info=True)
                finally:
                    self._jira = None


# ---------------------------------------------------------------------------
# Singleton-style factory for convenience (thread-safe)
# ---------------------------------------------------------------------------

_jira_client: JiraClient | None = None
_client_lock = threading.Lock()


def get_jira_client() -> JiraClient:
    """Return a process-wide cached JiraClient instance.

    This is the easiest way to get started, but the singleton is shared
    across the entire process. For tests or multiple Jira instances,
    prefer constructing JiraClient(settings=...) directly.
    """
    global _jira_client
    if _jira_client is None:
        with _client_lock:
            if _jira_client is None:
                _jira_client = JiraClient()
    return _jira_client


def reset_jira_client() -> None:
    """Reset the cached client returned by get_jira_client().

    Intended primarily for tests. Safe to call from application code
    if you need to force a fresh client (e.g. after credential rotation).
    """
    global _jira_client
    with _client_lock:
        if _jira_client is not None:
            _jira_client.close()
        _jira_client = None
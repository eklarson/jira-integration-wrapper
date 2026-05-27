class JiraIntegrationError(Exception):
    """Base exception for the Jira integration wrapper."""

    pass


class JiraAuthError(JiraIntegrationError):
    """Raised when authentication to Jira fails (bad credentials, missing token, etc.)."""

    pass


class JiraConnectionError(JiraIntegrationError):
    """Raised when a network or connection error occurs while talking to Jira."""

    pass
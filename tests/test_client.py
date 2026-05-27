"""Tests for JiraClient behavior (no real network calls)."""

from unittest.mock import MagicMock, patch

import pytest

from jira_integration_wrapper import (
    JiraClient,
    JiraSettings,
    get_jira_client,
    reset_jira_client,
)
from jira_integration_wrapper.exceptions import JiraConnectionError


@pytest.fixture(autouse=True)
def reset_singleton_between_tests():
    """Ensure the module singleton is clean before and after each test."""
    reset_jira_client()
    yield
    reset_jira_client()


def make_fake_settings():
    return JiraSettings(
        server="https://example.atlassian.net",
        email="user@example.com",
        api_token="fake-token",
    )


def test_client_accepts_explicit_settings():
    settings = make_fake_settings()
    client = JiraClient(settings=settings)
    assert client.settings is settings
    assert "example.atlassian.net" in repr(client)


@patch("jira_integration_wrapper.client.JIRA")
def test_lazy_connection_and_close(mock_jira_class):
    """The underlying JIRA client should only be created on first access."""
    mock_instance = MagicMock()
    mock_jira_class.return_value = mock_instance

    client = JiraClient(settings=make_fake_settings())

    # Not connected yet
    assert client._jira is None
    mock_jira_class.assert_not_called()

    # Trigger connection
    _ = client.jira
    mock_jira_class.assert_called_once()
    assert client._jira is mock_instance

    # Close should call close on the real client and clear the reference
    client.close()
    mock_instance.close.assert_called_once()
    assert client._jira is None


@patch("jira_integration_wrapper.client.JIRA")
def test_context_manager_closes_client(mock_jira_class):
    mock_instance = MagicMock()
    mock_jira_class.return_value = mock_instance

    with JiraClient(settings=make_fake_settings()) as client:
        _ = client.jira  # force connection

    mock_instance.close.assert_called_once()


@patch("jira_integration_wrapper.client.JIRA")
def test_reconnection_after_close(mock_jira_class):
    """After close(), accessing .jira again should create a new connection."""
    mock_instance_1 = MagicMock()
    mock_instance_2 = MagicMock()
    mock_jira_class.side_effect = [mock_instance_1, mock_instance_2]

    client = JiraClient(settings=make_fake_settings())
    assert client.jira is mock_instance_1

    client.close()
    assert client.jira is mock_instance_2
    assert mock_jira_class.call_count == 2


@patch("jira_integration_wrapper.client.JIRA")
def test_delegation_works(mock_jira_class):
    mock_instance = MagicMock()
    mock_instance.search_issues.return_value = ["issue1", "issue2"]
    mock_jira_class.return_value = mock_instance

    client = JiraClient(settings=make_fake_settings())
    result = client.search_issues("project = DEMO", maxResults=5)

    mock_instance.search_issues.assert_called_once_with("project = DEMO", maxResults=5)
    assert result == ["issue1", "issue2"]


def test_create_issue_simple_passes_issuetype():
    client = JiraClient(settings=make_fake_settings())

    mock_jira = MagicMock()
    mock_jira.create_issue.return_value = "new-issue"
    client._jira = mock_jira

    client.create_issue_simple(
        project="PROJ",
        summary="Test",
        description="Desc",
        issuetype="Bug",
        labels=["urgent"],
    )

    mock_jira.create_issue.assert_called_once()
    fields = mock_jira.create_issue.call_args.kwargs["fields"]
    assert fields["issuetype"] == {"name": "Bug"}
    assert fields["labels"] == ["urgent"]


def test_singleton_and_reset(monkeypatch):
    monkeypatch.setenv("JIRA_SERVER", "https://example.atlassian.net")
    monkeypatch.setenv("JIRA_EMAIL", "u@example.com")
    monkeypatch.setenv("JIRA_API_TOKEN", "tok")

    c1 = get_jira_client()
    c2 = get_jira_client()
    assert c1 is c2

    reset_jira_client()
    c3 = get_jira_client()
    assert c3 is not c1


@patch("jira_integration_wrapper.client.JIRA")
def test_connection_error_is_wrapped(mock_jira_class):
    from jira.exceptions import JIRAError

    mock_jira_class.side_effect = JIRAError("boom")

    client = JiraClient(settings=make_fake_settings())

    with pytest.raises(JiraConnectionError, match="Failed to connect"):
        _ = client.jira

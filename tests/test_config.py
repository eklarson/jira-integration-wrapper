"""Tests for configuration loading (no network)."""

import json
from unittest.mock import patch

import pytest

from jira_integration_wrapper.config import (
    JiraSettings,
    get_jira_settings,
)
from jira_integration_wrapper.exceptions import JiraConfigError


def test_get_jira_settings_explicit_values(monkeypatch):
    """Direct env vars (no .env file) should produce correct settings."""
    monkeypatch.delenv("JIRA_PROXIES", raising=False)
    monkeypatch.delenv("JIRA_HTTP_PROXY", raising=False)
    monkeypatch.delenv("JIRA_HTTPS_PROXY", raising=False)

    monkeypatch.setenv("JIRA_SERVER", "https://example.atlassian.net")
    monkeypatch.setenv("JIRA_EMAIL", "user@example.com")
    monkeypatch.setenv("JIRA_API_TOKEN", "token123")
    monkeypatch.setenv("JIRA_VERIFY_SSL", "false")

    # We pass load_env=False so we don't accidentally load a real .env
    settings = get_jira_settings(load_env=False)

    assert settings.server == "https://example.atlassian.net"
    assert settings.email == "user@example.com"
    assert settings.api_token == "token123"
    assert settings.verify_ssl is False
    assert settings.token_auth is None
    assert settings.has_auth() is True


def test_proxies_from_json(monkeypatch):
    monkeypatch.setenv("JIRA_SERVER", "https://example.atlassian.net")
    monkeypatch.setenv("JIRA_TOKEN_AUTH", "pat-xyz")
    monkeypatch.setenv(
        "JIRA_PROXIES", json.dumps({"https": "http://proxy:8080", "http": "http://proxy:8080"})
    )

    settings = get_jira_settings(load_env=False)
    assert settings.proxies == {"https": "http://proxy:8080", "http": "http://proxy:8080"}


def test_proxies_from_separate_vars(monkeypatch):
    monkeypatch.setenv("JIRA_SERVER", "https://example.atlassian.net")
    monkeypatch.setenv("JIRA_TOKEN_AUTH", "pat-xyz")
    monkeypatch.setenv("JIRA_HTTP_PROXY", "http://http-proxy:3128")
    monkeypatch.setenv("JIRA_HTTPS_PROXY", "http://https-proxy:3128")

    settings = get_jira_settings(load_env=False)
    assert settings.proxies == {
        "http": "http://http-proxy:3128",
        "https": "http://https-proxy:3128",
    }


def test_missing_server_raises_clear_error(monkeypatch):
    monkeypatch.delenv("JIRA_SERVER", raising=False)
    with pytest.raises(JiraConfigError, match="JIRA_SERVER"):
        get_jira_settings(load_env=False)


@patch("jira_integration_wrapper.config._ensure_dotenv_loaded")
def test_missing_auth_raises_clear_error_when_load_env(mock_load_dotenv, monkeypatch):
    """When load_env=True and no auth is present, we should fail fast."""
    monkeypatch.setenv("JIRA_SERVER", "https://example.atlassian.net")
    monkeypatch.delenv("JIRA_EMAIL", raising=False)
    monkeypatch.delenv("JIRA_API_TOKEN", raising=False)
    monkeypatch.delenv("JIRA_TOKEN_AUTH", raising=False)

    with pytest.raises(JiraConfigError, match="No Jira authentication"):
        get_jira_settings(load_env=True)

    mock_load_dotenv.assert_called_once()


def test_jira_settings_direct_construction_allows_incomplete():
    """Direct construction (useful for tests) should not require auth."""
    s = JiraSettings(server="https://example.com")
    assert s.has_auth() is False
    assert s.server == "https://example.com"


def test_invalid_proxies_json_logs_warning_and_falls_back(monkeypatch, caplog):
    monkeypatch.setenv("JIRA_SERVER", "https://example.atlassian.net")
    monkeypatch.setenv("JIRA_TOKEN_AUTH", "pat-xyz")
    monkeypatch.setenv("JIRA_PROXIES", "not-valid-json")
    monkeypatch.setenv("JIRA_HTTPS_PROXY", "http://https-proxy:3128")

    with caplog.at_level("WARNING"):
        settings = get_jira_settings(load_env=False)

    assert settings.proxies == {"https": "http://https-proxy:3128"}
    assert "Invalid JIRA_PROXIES JSON" in caplog.text

"""Tests for package metadata."""

from jira_integration_wrapper import __version__


def test_version_matches_project_metadata():
    assert __version__ == "0.2.0"

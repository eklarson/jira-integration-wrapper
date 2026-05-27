# jira-integration-wrapper

A clean, opinionated Python wrapper around the official `jira` package that completely abstracts away server URL and authentication configuration.

## Why?

Tired of repeating `JIRA(server=..., basic_auth=...)` or `token_auth=...` in every script? This wrapper centralizes configuration (via environment variables) and gives you a simple `JiraClient` that just works.

## Features

- Lazy connection (only connects when you actually use it)
- Supports both Jira Cloud (email + API token) and Jira Server/Data Center (PAT)
- Transparent delegation to the underlying `jira` client (you still have access to every method)
- Context manager support for automatic cleanup
- Convenience helper: `create_issue_simple`
- Clear error handling with specific exception types
- Proxy support and SSL verification control
- Works great with Docker, CI, Kubernetes, etc.

## Installation

```bash
pip install git+https://github.com/eklarson/jira-integration-wrapper.git
```

Or for development:

```bash
git clone https://github.com/eklarson/jira-integration-wrapper.git
cd jira-integration-wrapper
pip install -e .
```

## Quick Start

```python
from jira_integration_wrapper import get_jira_client

client = get_jira_client()

# Search issues
issues = client.search_issues("project = PROJ AND status = 'In Progress'", maxResults=20)

for issue in issues:
    print(issue.key, issue.fields.summary)

# Create a simple issue
new_issue = client.create_issue_simple(
    project="PROJ",
    summary="Something needs attention",
    description="Details...",
)
```

## Resource Management

`JiraClient` holds a network session. Use the context manager for automatic cleanup:

```python
from jira_integration_wrapper import JiraClient

with JiraClient() as client:
    issues = client.search_issues("project = PROJ", maxResults=50)
    # session is closed automatically when the block exits
```

You can also call `client.close()` explicitly, or use the module-level helper:

```python
from jira_integration_wrapper import get_jira_client, reset_jira_client

client = get_jira_client()
...
reset_jira_client()   # useful in tests or after rotating credentials
```

## Testing & Advanced Usage

You can construct a client without touching environment variables:

```python
from jira_integration_wrapper import JiraClient, JiraSettings

settings = JiraSettings(
    server="https://yourcompany.atlassian.net",
    email="...",
    api_token="...",
)
client = JiraClient(settings=settings)
```

This is the recommended pattern inside test suites. You can also monkey-patch `get_jira_settings` or replace the `.jira` attribute with a mock after construction.

## Configuration (Environment Variables)

Create a `.env` file (or set the variables in your environment / Docker / Kubernetes):

```env
JIRA_SERVER=https://yourcompany.atlassian.net

# Jira Cloud
JIRA_EMAIL=your.email@company.com
JIRA_API_TOKEN=your_api_token_from_id.atlassian.com

# OR Jira Server / Data Center (Personal Access Token)
# JIRA_TOKEN_AUTH=your_pat_here
```

### Optional Variables

| Variable              | Default | Description |
|-----------------------|---------|-------------|
| `JIRA_VERIFY_SSL`     | `true`  | Set to `false` only when you must disable certificate verification |
| `JIRA_PROXIES`        | —       | JSON object, e.g. `{"https": "http://proxy:8080"}` |
| `JIRA_HTTP_PROXY`     | —       | Alternative to `JIRA_PROXIES` |
| `JIRA_HTTPS_PROXY`    | —       | Alternative to `JIRA_PROXIES` |

**Never commit your `.env` file!**

## Project Structure

```
jira-integration-wrapper/
├── src/
│   └── jira_integration_wrapper/
│       ├── __init__.py
│       ├── client.py
│       ├── config.py
│       └── exceptions.py
├── tests/
├── pyproject.toml
├── README.md
├── .env.example
└── LICENSE
```

## Development

```bash
pip install -e ".[dev]"
ruff check .
ruff format .
mypy --strict src
pytest
```

## License
MIT
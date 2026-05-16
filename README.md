# jira-integration-wrapper

A clean, opinionated Python wrapper around the official `jira` package that completely abstracts away server URL and authentication configuration.

## Why?

Tired of repeating `JIRA(server=..., basic_auth=...)` or `token_auth=...` in every script? This wrapper centralizes configuration (via environment variables) and gives you a simple `JiraClient` that just works.

## Features

- Lazy connection (only connects when you actually use it)
- Supports both Jira Cloud (email + API token) and Jira Server/Data Center (PAT via token_auth)
- Full delegation to the underlying `jira` client — you still have access to every method
- Easy helper methods (e.g. `create_issue_simple`)
- Proper error handling and logging
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

## Configuration (Environment Variables)

Create a `.env` file (or set in your environment):

```env
JIRA_SERVER=https://yourcompany.atlassian.net
JIRA_EMAIL=your.email@company.com          # For Jira Cloud
JIRA_API_TOKEN=your_atlassian_api_token   # For Jira Cloud

# OR for Jira Server / Data Center
# JIRA_TOKEN_AUTH=your_personal_access_token
```

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
├── pyproject.toml
├── README.md
└── .env.example
```

## Development

```bash
pip install -e "[dev]"
ruff check .
```

## License
MIT
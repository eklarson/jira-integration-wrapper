#!/usr/bin/env python3
"""
Example script: Create a Jira issue using jira-integration-wrapper + your .env file.

This script demonstrates the simplest way to create an issue while relying on
the configuration in your .env file (JIRA_SERVER, JIRA_EMAIL + JIRA_API_TOKEN,
or JIRA_TOKEN_AUTH, etc.).

------------------------------------------------------------------------------
How to run this script
------------------------------------------------------------------------------

Option A - Recommended (after installing the package):
    pip install -e .
    python examples/create_issue.py -p SCRUM -s "Fix the bug"

Option B - Run directly from source (no install needed):
    # From the repository root
    ./examples/create_issue.py -p SCRUM -s "Something needs attention"

    # Or from inside the examples directory
    cd examples
    ./create_issue.py -p SCRUM -s "Something needs attention"

The script will automatically find the local package when run from the source tree.

Usage examples:
    # Basic usage
    python examples/create_issue.py -p SCRUM -s "Something broke"

    # With description and confirmation skip
    python examples/create_issue.py -p SCRUM -s "Fix login bug" -d "..." -y

    # List your available projects
    python examples/create_issue.py --list-projects

    # Dry run (safe - does not actually create anything)
    python examples/create_issue.py -p SCRUM -s "Test issue" --dry-run

Requirements:
    - Your .env file must be present in the current working directory (or variables exported)
"""

import argparse
import os
import sys
from typing import NoReturn

# ---------------------------------------------------------------------------
# Allow running this script directly from the source tree without installing
# the package first. This makes examples much more developer-friendly.
#
# Because this project uses a src/ layout, we need to add the src directory
# to sys.path, not just the repository root.
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

try:
    from jira_integration_wrapper import get_jira_client
except ModuleNotFoundError as e:
    if "jira" in str(e):
        print(
            "ERROR: Missing dependency 'jira'.\n"
            "Please install the package with its dependencies first:\n\n"
            "    pip install -e '.[dev]'\n",
            file=sys.stderr,
        )
    else:
        print(
            "ERROR: Could not import jira_integration_wrapper.\n"
            "Make sure you are running this from the repository root or the examples/ directory.\n",
            file=sys.stderr,
        )
    sys.exit(1)


def list_accessible_projects() -> None:
    """Connect to Jira and print all projects the user can see."""
    print("→ Loading Jira client from environment (.env file)...")
    client = get_jira_client()

    print(f"Connecting to Jira at {client.settings.server}...\n")
    print("Your accessible projects:\n")

    try:
        projects = client.projects()
        if not projects:
            print("  (No projects found)")
            return

        for p in projects:
            print(f"  {p.key:12}  {p.name}")

    except Exception as exc:
        print(f"❌ Failed to list projects: {exc}", file=sys.stderr)
        sys.exit(1)


def create_issue(
    project: str,
    summary: str,
    description: str = "",
    issuetype: str = "Task",
    dry_run: bool = False,
    skip_confirmation: bool = False,
) -> None:
    """
    Create a Jira issue (or simulate it in dry-run mode).
    """
    if dry_run:
        print("🔍 DRY RUN MODE - No issue will be created\n")
        print(f"Project:     {project}")
        print(f"Summary:     {summary}")
        print(f"Description: {description or '(empty)'}")
        print(f"Issue Type:  {issuetype}")
        print("\n✅ Dry run complete. Remove --dry-run to actually create the issue.")
        return

    # This is the normal, recommended way to get a client.
    # It will automatically load configuration from your .env file.
    print("→ Loading Jira client from environment (.env file)...")
    client = get_jira_client()

    print(f"Connecting to Jira at {client.settings.server}...\n")

    # Confirmation prompt for real issue creation
    if not skip_confirmation:
        print("You are about to create a REAL issue in Jira.")
        print(f"  Project:    {project}")
        print(f"  Summary:    {summary}")
        print(f"  Issue Type: {issuetype}")
        if description:
            print(f"  Description: {description[:80]}{'...' if len(description) > 80 else ''}")
        print()
        answer = input("Proceed? [y/N]: ").strip().lower()
        if answer not in ("y", "yes"):
            print("Aborted.")
            sys.exit(0)

    try:
        issue = client.create_issue_simple(
            project=project,
            summary=summary,
            description=description,
            issuetype=issuetype,
        )

        # The returned object is a jira.resources.Issue from the underlying library
        print("\n✅ Issue created successfully!")
        print(f"   Key:        {issue.key}")
        print(f"   Summary:    {issue.fields.summary}")
        print(f"   Status:     {issue.fields.status}")
        print(f"   Assignee:   {getattr(issue.fields.assignee, 'displayName', 'Unassigned')}")
        print(f"   URL:        {issue.permalink()}")

    except Exception as exc:
        # Provide friendlier messages for common errors
        error_str = str(exc)
        if "project" in error_str.lower() and (
            "doesn't exist" in error_str or "permission" in error_str
        ):
            print(
                f"\n❌ Error: The project '{project}' does not exist or you don't have permission "
                "to create issues in it.",
                file=sys.stderr,
            )
            print(
                "   Tip: Run with --list-projects to see the projects you have access to.",
                file=sys.stderr,
            )
        else:
            print(f"\n❌ Failed to create issue: {exc}", file=sys.stderr)
        sys.exit(1)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a Jira issue using your .env configuration.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "-p",
        "--project",
        help="Jira project key (e.g. SCRUM, TEAM, OPS). Required unless --list-projects is used.",
    )
    parser.add_argument(
        "-s",
        "--summary",
        help="Short summary / title of the issue. Required unless --list-projects is used.",
    )
    parser.add_argument(
        "-d",
        "--description",
        default="",
        help="Detailed description of the issue",
    )
    parser.add_argument(
        "--issuetype",
        default="Task",
        help="Issue type name (Task, Bug, Story, etc.)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be created without actually creating the issue",
    )
    parser.add_argument(
        "-y",
        "--yes",
        action="store_true",
        help="Skip the confirmation prompt before creating a real issue",
    )
    parser.add_argument(
        "--list-projects",
        action="store_true",
        help="List all projects you have access to and exit",
    )

    return parser.parse_args()


def main() -> NoReturn:
    args = parse_args()

    # Handle --list-projects mode (doesn't require project/summary)
    if args.list_projects:
        list_accessible_projects()
        sys.exit(0)

    # For normal creation mode, project and summary are required
    if not args.project or not args.summary:
        print(
            "Error: --project and --summary are required when not using --list-projects.",
            file=sys.stderr,
        )
        sys.exit(1)

    create_issue(
        project=args.project,
        summary=args.summary,
        description=args.description,
        issuetype=args.issuetype,
        dry_run=args.dry_run,
        skip_confirmation=args.yes,
    )

    sys.exit(0)


if __name__ == "__main__":
    main()

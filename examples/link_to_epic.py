#!/usr/bin/env python3
"""
Utility script: Link existing issues to an Epic in Jira.

This is useful for organizing work under a high-level Epic (such as a project objective
or major initiative).

Usage examples:

    # Link several issues to an Epic
    python examples/link_to_epic.py --epic SCRUM-12 SCRUM-4 SCRUM-5 SCRUM-6 SCRUM-7

    # With confirmation
    python examples/link_to_epic.py -e SCRUM-12 SCRUM-4 SCRUM-5 --yes

Requirements:
    - The jira-integration-wrapper package installed
    - Valid Jira credentials in your .env file
"""

import argparse
import os
import sys
from typing import List

# Allow running directly from the source tree without installing the package.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from jira_integration_wrapper import get_jira_client


def find_epic_link_field(client) -> str | None:
    """
    Try to discover the 'Epic Link' custom field ID.
    This field name varies across Jira instances.
    """
    try:
        fields = client.fields()
        for f in fields:
            if f.get("name", "").lower() in ("epic link", "epic"):
                return f["id"]
    except Exception:
        pass
    return None


def link_issues_to_epic(epic_key: str, issue_keys: List[str], dry_run: bool = False) -> None:
    client = get_jira_client()

    print(f"Connecting to Jira at {client.settings.server}...\n")

    success = []
    failed = []

    for key in issue_keys:
        try:
            if dry_run:
                print(f"[DRY RUN] Would link {key} → Epic {epic_key}")
                success.append(key)
                continue

            # Preferred method: Use the library's add_issues_to_epic helper
            # This works well when the target is a real Epic.
            try:
                client.add_issues_to_epic(epic_key, [key])
                print(f"✅ Linked {key} to Epic {epic_key} (via add_issues_to_epic)")
                success.append(key)
                continue
            except Exception:
                pass  # Fall through to other methods

            # Fallback 1: Try to discover and set the Epic Link custom field
            epic_field = find_epic_link_field(client)
            if epic_field:
                issue = client.issue(key)
                issue.update(fields={epic_field: epic_key})
                print(f"✅ Linked {key} to Epic {epic_key} (via Epic Link field)")
                success.append(key)
                continue

            # Fallback 2: Create a "Relates" issue link
            client.create_issue_link(
                type="Relates",
                inwardIssue=key,
                outwardIssue=epic_key,
            )
            print(f"✅ Created 'Relates' link from {key} to {epic_key}")
            success.append(key)

        except Exception as exc:
            print(f"❌ Failed to link {key}: {exc}")
            failed.append(key)

    print("\n--- Summary ---")
    print(f"Successfully linked: {len(success)}")
    if failed:
        print(f"Failed: {len(failed)} → {', '.join(failed)}")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Link one or more Jira issues to an Epic."
    )
    parser.add_argument(
        "-e", "--epic",
        required=True,
        help="The Epic key to link issues to (e.g. SCRUM-12)",
    )
    parser.add_argument(
        "issues",
        nargs="+",
        help="Issue keys to link to the Epic (e.g. SCRUM-4 SCRUM-5 ...)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be linked without making changes",
    )
    parser.add_argument(
        "-y", "--yes",
        action="store_true",
        help="Skip confirmation prompt",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    print(f"About to link the following issues to Epic {args.epic}:")
    for key in args.issues:
        print(f"  - {key}")

    if not args.yes and not args.dry_run:
        answer = input("\nProceed? [y/N]: ").strip().lower()
        if answer not in ("y", "yes"):
            print("Aborted.")
            sys.exit(0)

    link_issues_to_epic(
        epic_key=args.epic,
        issue_keys=args.issues,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()

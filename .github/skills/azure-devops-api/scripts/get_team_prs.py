#!/usr/bin/env python3
"""
Get pull requests where a specific team (or user) is assigned as a reviewer.

Uses the project-level PR endpoint with searchCriteria.reviewerId filter.

Usage:
    python get_team_prs.py --org <org> --project <project> --reviewer-id <guid> [--status active]

Environment variables:
    AZURE_DEVOPS_PAT: Personal Access Token for Azure DevOps

Output:
    JSON array of pull requests with key details
"""

import argparse
import base64
import json
import os
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone


def get_auth_header(pat: str) -> dict:
    """Create authorization header from PAT."""
    credentials = base64.b64encode(f":{pat}".encode()).decode()
    return {"Authorization": f"Basic {credentials}"}


def api_request(url: str, headers: dict) -> dict:
    """Make a GET request to the Azure DevOps API."""
    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request) as response:
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as e:
        error_body = e.read().decode() if e.fp else ""
        print(json.dumps({
            "error": True,
            "status": e.code,
            "message": str(e.reason),
            "details": error_body
        }))
        sys.exit(1)


def calculate_age_days(date_str: str) -> int:
    """Calculate days since a date string."""
    if not date_str:
        return 0
    created = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    now = datetime.now(timezone.utc)
    return (now - created).days


def format_pr(pr: dict, org: str, project: str) -> dict:
    """Format a PR into a simplified structure."""
    repo = pr.get("repository", {})
    repo_name = repo.get("name", "unknown")
    pr_id = pr.get("pullRequestId")
    
    return {
        "id": pr_id,
        "repository": repo_name,
        "title": pr.get("title"),
        "description": pr.get("description", "")[:200],  # Truncate long descriptions
        "author": pr.get("createdBy", {}).get("displayName", "Unknown"),
        "authorId": pr.get("createdBy", {}).get("id", ""),
        "status": pr.get("status"),
        "sourceBranch": pr.get("sourceRefName", "").replace("refs/heads/", ""),
        "targetBranch": pr.get("targetRefName", "").replace("refs/heads/", ""),
        "createdDate": pr.get("creationDate"),
        "ageDays": calculate_age_days(pr.get("creationDate")),
        "isDraft": pr.get("isDraft", False),
        "reviewers": [
            {
                "name": r.get("displayName"),
                "vote": r.get("vote"),
                "isRequired": r.get("isRequired", False)
            }
            for r in pr.get("reviewers", [])
        ],
        "webUrl": f"https://dev.azure.com/{org}/{project}/_git/{repo_name}/pullrequest/{pr_id}"
    }


def main():
    parser = argparse.ArgumentParser(description="Get PRs where reviewer matches the given ID")
    parser.add_argument("--org", required=True, help="Azure DevOps organization name")
    parser.add_argument("--project", required=True, help="Azure DevOps project name")
    parser.add_argument("--reviewer-id", required=True, help="Reviewer GUID (team or user)")
    parser.add_argument("--status", default="active", choices=["active", "completed", "abandoned", "all"],
                        help="PR status filter (default: active)")
    parser.add_argument("--exclude-author-id", help="Exclude PRs created by this user ID")
    
    args = parser.parse_args()
    
    pat = os.environ.get("AZURE_DEVOPS_PAT")
    if not pat:
        print(json.dumps({"error": True, "message": "AZURE_DEVOPS_PAT environment variable not set"}))
        sys.exit(1)
    
    headers = get_auth_header(pat)
    
    # Build the URL with search criteria
    url = (
        f"https://dev.azure.com/{args.org}/{args.project}/_apis/git/pullrequests"
        f"?searchCriteria.reviewerId={args.reviewer_id}"
        f"&searchCriteria.status={args.status}"
        f"&api-version=7.1"
    )
    
    response = api_request(url, headers)
    prs = response.get("value", [])
    
    # Filter out PRs by excluded author if specified
    if args.exclude_author_id:
        prs = [
            pr for pr in prs
            if pr.get("createdBy", {}).get("id", "").lower() != args.exclude_author_id.lower()
        ]
    
    # Format results
    formatted_prs = [format_pr(pr, args.org, args.project) for pr in prs]
    
    # Sort by age (oldest first)
    formatted_prs.sort(key=lambda x: x["ageDays"], reverse=True)
    
    print(json.dumps({
        "count": len(formatted_prs),
        "pullRequests": formatted_prs
    }, indent=2))


if __name__ == "__main__":
    main()


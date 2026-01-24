#!/usr/bin/env python3
"""
Get pull requests where a specific team (or user) is assigned as a reviewer.

Usage:
    python get_team_prs.py --org <org> --project <project> --team-id <team-guid> [--user-id <user-guid>] [--status active]

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


def get_repositories(org: str, project: str, headers: dict) -> list:
    """Get all repositories in the project."""
    url = f"https://dev.azure.com/{org}/{project}/_apis/git/repositories?api-version=7.1"
    response = api_request(url, headers)
    return response.get("value", [])


def get_pull_requests_for_repo(
    org: str, 
    project: str, 
    repo_id: str, 
    status: str,
    headers: dict
) -> list:
    """Get pull requests for a specific repository."""
    url = (
        f"https://dev.azure.com/{org}/{project}/_apis/git/repositories/{repo_id}"
        f"/pullrequests?searchCriteria.status={status}&api-version=7.1"
    )
    response = api_request(url, headers)
    return response.get("value", [])


def filter_prs_by_reviewer(prs: list, team_id: str, user_id: str = None) -> list:
    """Filter PRs where the team or user is a reviewer."""
    filtered = []
    reviewer_ids = {team_id.lower()}
    if user_id:
        reviewer_ids.add(user_id.lower())
    
    for pr in prs:
        reviewers = pr.get("reviewers", [])
        for reviewer in reviewers:
            reviewer_id = reviewer.get("id", "").lower()
            if reviewer_id in reviewer_ids:
                filtered.append(pr)
                break
    
    return filtered


def calculate_age_days(date_str: str) -> int:
    """Calculate days since a date string."""
    if not date_str:
        return 0
    # Parse ISO format date
    created = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    now = datetime.now(timezone.utc)
    return (now - created).days


def format_pr(pr: dict, repo_name: str) -> dict:
    """Format a PR into a simplified structure."""
    return {
        "id": pr.get("pullRequestId"),
        "repository": repo_name,
        "title": pr.get("title"),
        "description": pr.get("description", ""),
        "author": pr.get("createdBy", {}).get("displayName", "Unknown"),
        "authorEmail": pr.get("createdBy", {}).get("uniqueName", ""),
        "status": pr.get("status"),
        "sourceBranch": pr.get("sourceRefName", "").replace("refs/heads/", ""),
        "targetBranch": pr.get("targetRefName", "").replace("refs/heads/", ""),
        "createdDate": pr.get("creationDate"),
        "ageDays": calculate_age_days(pr.get("creationDate")),
        "isDraft": pr.get("isDraft", False),
        "reviewers": [
            {
                "name": r.get("displayName"),
                "vote": r.get("vote"),  # 10=approved, 5=approved with suggestions, 0=no vote, -5=waiting, -10=rejected
                "isRequired": r.get("isRequired", False)
            }
            for r in pr.get("reviewers", [])
        ],
        "url": pr.get("url"),
        "webUrl": f"https://dev.azure.com/{pr.get('repository', {}).get('project', {}).get('name', '')}/{pr.get('repository', {}).get('project', {}).get('name', '')}/_git/{repo_name}/pullrequest/{pr.get('pullRequestId')}"
    }


def main():
    parser = argparse.ArgumentParser(description="Get PRs where team is a reviewer")
    parser.add_argument("--org", required=True, help="Azure DevOps organization name")
    parser.add_argument("--project", required=True, help="Azure DevOps project name")
    parser.add_argument("--team-id", required=True, help="Team GUID to filter by")
    parser.add_argument("--user-id", help="Optional user GUID to also include")
    parser.add_argument("--status", default="active", choices=["active", "completed", "abandoned", "all"],
                        help="PR status filter (default: active)")
    parser.add_argument("--exclude-author", help="Exclude PRs created by this user ID")
    
    args = parser.parse_args()
    
    pat = os.environ.get("AZURE_DEVOPS_PAT")
    if not pat:
        print(json.dumps({"error": True, "message": "AZURE_DEVOPS_PAT environment variable not set"}))
        sys.exit(1)
    
    headers = get_auth_header(pat)
    
    # Get all repositories
    repos = get_repositories(args.org, args.project, headers)
    
    all_prs = []
    
    # Get PRs from each repository
    for repo in repos:
        repo_id = repo.get("id")
        repo_name = repo.get("name")
        
        prs = get_pull_requests_for_repo(args.org, args.project, repo_id, args.status, headers)
        
        # Filter by reviewer
        filtered_prs = filter_prs_by_reviewer(prs, args.team_id, args.user_id)
        
        # Exclude PRs by specific author if requested
        if args.exclude_author:
            filtered_prs = [
                pr for pr in filtered_prs 
                if pr.get("createdBy", {}).get("id", "").lower() != args.exclude_author.lower()
            ]
        
        # Format and add to results
        for pr in filtered_prs:
            all_prs.append(format_pr(pr, repo_name))
    
    # Sort by age (oldest first, as they need attention)
    all_prs.sort(key=lambda x: x["ageDays"], reverse=True)
    
    print(json.dumps({
        "count": len(all_prs),
        "pullRequests": all_prs
    }, indent=2))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Query pull requests where a team is assigned as reviewer.
Uses environment variables for Azure DevOps configuration.
"""

import argparse
import json
import os
import sys
from datetime import datetime
from urllib.request import Request, urlopen
from urllib.error import HTTPError
import base64


def get_env_or_exit(name):
    """Get environment variable or exit with error."""
    value = os.environ.get(name)
    if not value:
        print(json.dumps({"error": True, "message": f"{name} environment variable not set"}))
        sys.exit(1)
    return value


def get_env_optional(name):
    """Get optional environment variable."""
    return os.environ.get(name)


def get_auth_header():
    pat = get_env_or_exit("AZURE_DEVOPS_PAT")
    token = base64.b64encode(f":{pat}".encode()).decode()
    return {"Authorization": f"Basic {token}"}


def get_prs(org, project, reviewer_id, status, headers):
    """Get PRs where reviewer is assigned."""
    url = f"https://dev.azure.com/{org}/{project}/_apis/git/pullrequests?searchCriteria.reviewerId={reviewer_id}&searchCriteria.status={status}&api-version=7.1"
    try:
        req = Request(url, headers=headers)
        with urlopen(req) as response:
            return json.loads(response.read().decode()).get("value", []), None
    except HTTPError as e:
        return None, {"error": True, "status": e.code, "message": e.reason}


def main():
    parser = argparse.ArgumentParser(description="Get PRs for team review")
    parser.add_argument("--status", default="active", help="PR status (default: active)")
    parser.add_argument("--include-own", action="store_true", help="Include your own PRs")
    args = parser.parse_args()

    # Get configuration from environment variables
    org = get_env_or_exit("AZURE_DEVOPS_ORG")
    project = get_env_or_exit("AZURE_DEVOPS_PROJECT")
    team_id = get_env_or_exit("AZURE_DEVOPS_TEAM_ID")
    user_id = get_env_optional("AZURE_DEVOPS_USER_ID")
    headers = get_auth_header()

    prs, err = get_prs(org, project, team_id, args.status, headers)
    if err:
        print(json.dumps(err))
        sys.exit(1)

    # Filter out user's own PRs unless --include-own
    if user_id and not args.include_own:
        prs = [pr for pr in prs if pr.get("createdBy", {}).get("id") != user_id]

    now = datetime.utcnow()
    output = {
        "org": org,
        "project": project,
        "teamId": team_id,
        "count": len(prs),
        "pullRequests": []
    }

    for pr in prs:
        created = datetime.fromisoformat(pr.get("creationDate", "").replace("Z", "+00:00"))
        age_days = (now - created.replace(tzinfo=None)).days

        output["pullRequests"].append({
            "id": pr["pullRequestId"],
            "title": pr["title"],
            "repository": pr["repository"]["name"],
            "author": pr["createdBy"]["displayName"],
            "isDraft": pr.get("isDraft", False),
            "status": "Draft" if pr.get("isDraft", False) else "Ready",
            "ageDays": age_days,
            "webUrl": f"https://dev.azure.com/{org}/{project}/_git/{pr['repository']['name']}/pullrequest/{pr['pullRequestId']}"
        })

    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()

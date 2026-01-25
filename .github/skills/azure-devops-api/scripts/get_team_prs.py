#!/usr/bin/env python3
"""
Get pull requests where a specific reviewer (team or user) is assigned.
Uses Azure DevOps REST API searchCriteria.reviewerId filter.
"""

import argparse
import json
import os
import sys
from datetime import datetime
from urllib.request import Request, urlopen
from urllib.error import HTTPError
import base64


def get_auth_header():
    pat = os.environ.get("AZURE_DEVOPS_PAT")
    if not pat:
        return None, "AZURE_DEVOPS_PAT environment variable not set"
    token = base64.b64encode(f":{pat}".encode()).decode()
    return {"Authorization": f"Basic {token}"}, None


def main():
    parser = argparse.ArgumentParser(description="Get PRs for a team/user reviewer")
    parser.add_argument("--org", required=True, help="Azure DevOps organization")
    parser.add_argument("--project", required=True, help="Project name")
    parser.add_argument("--reviewer-id", required=True, help="Reviewer GUID (team or user)")
    parser.add_argument("--status", default="active", choices=["active", "completed", "abandoned", "all"])
    parser.add_argument("--exclude-author-id", help="Exclude PRs by this author")
    args = parser.parse_args()

    headers, err = get_auth_header()
    if err:
        print(json.dumps({"error": True, "message": err}))
        sys.exit(1)

    url = f"https://dev.azure.com/{args.org}/{args.project}/_apis/git/pullrequests?searchCriteria.reviewerId={args.reviewer_id}&searchCriteria.status={args.status}&api-version=7.1"

    try:
        req = Request(url, headers=headers)
        with urlopen(req) as response:
            data = json.loads(response.read().decode())
    except HTTPError as e:
        print(json.dumps({"error": True, "status": e.code, "message": e.reason}))
        sys.exit(1)

    prs = data.get("value", [])
    now = datetime.utcnow()

    output = {"count": 0, "pullRequests": []}

    for pr in prs:
        author_id = pr.get("createdBy", {}).get("id")
        if args.exclude_author_id and author_id == args.exclude_author_id:
            continue

        created = datetime.fromisoformat(pr["creationDate"].replace("Z", "+00:00"))
        age_days = (now - created.replace(tzinfo=None)).days

        output["pullRequests"].append({
            "id": pr["pullRequestId"],
            "repository": pr["repository"]["name"],
            "title": pr["title"],
            "author": pr["createdBy"]["displayName"],
            "authorId": author_id,
            "status": pr["status"],
            "sourceBranch": pr["sourceRefName"].replace("refs/heads/", ""),
            "targetBranch": pr["targetRefName"].replace("refs/heads/", ""),
            "createdDate": pr["creationDate"],
            "ageDays": age_days,
            "isDraft": pr.get("isDraft", False),
            "reviewers": [
                {"name": r["displayName"], "vote": r.get("vote", 0), "isRequired": r.get("isRequired", False)}
                for r in pr.get("reviewers", [])
            ],
            "webUrl": f"https://dev.azure.com/{args.org}/{args.project}/_git/{pr['repository']['name']}/pullrequest/{pr['pullRequestId']}"
        })

    output["count"] = len(output["pullRequests"])
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Get the files and diffs for a pull request.

Usage:
    python get_pr_diff.py --org <org> --project <project> --repo <repo-name> --pr-id <pr-id> [--file <path>]

Environment variables:
    AZURE_DEVOPS_PAT: Personal Access Token for Azure DevOps

Output:
    JSON with changed files and their diffs
"""

import argparse
import base64
import json
import os
import sys
import urllib.request
import urllib.error
from typing import Optional


def get_auth_header(pat: str) -> dict:
    """Create authorization header from PAT."""
    credentials = base64.b64encode(f":{pat}".encode()).decode()
    return {"Authorization": f"Basic {credentials}"}


def api_request(url: str, headers: dict, accept: str = "application/json") -> bytes:
    """Make a GET request to the Azure DevOps API."""
    request_headers = {**headers, "Accept": accept}
    request = urllib.request.Request(url, headers=request_headers)
    try:
        with urllib.request.urlopen(request) as response:
            return response.read()
    except urllib.error.HTTPError as e:
        error_body = e.read().decode() if e.fp else ""
        print(json.dumps({
            "error": True,
            "status": e.code,
            "message": str(e.reason),
            "details": error_body
        }))
        sys.exit(1)


def get_pr_details(org: str, project: str, repo: str, pr_id: int, headers: dict) -> dict:
    """Get pull request details."""
    url = (
        f"https://dev.azure.com/{org}/{project}/_apis/git/repositories/{repo}"
        f"/pullrequests/{pr_id}?api-version=7.1"
    )
    response = api_request(url, headers)
    return json.loads(response.decode())


def get_pr_iterations(org: str, project: str, repo: str, pr_id: int, headers: dict) -> list:
    """Get PR iterations (each push to the PR creates an iteration)."""
    url = (
        f"https://dev.azure.com/{org}/{project}/_apis/git/repositories/{repo}"
        f"/pullrequests/{pr_id}/iterations?api-version=7.1"
    )
    response = api_request(url, headers)
    data = json.loads(response.decode())
    return data.get("value", [])


def get_iteration_changes(
    org: str, 
    project: str, 
    repo: str, 
    pr_id: int, 
    iteration_id: int,
    headers: dict
) -> list:
    """Get changes in a specific iteration."""
    url = (
        f"https://dev.azure.com/{org}/{project}/_apis/git/repositories/{repo}"
        f"/pullrequests/{pr_id}/iterations/{iteration_id}/changes?api-version=7.1"
    )
    response = api_request(url, headers)
    data = json.loads(response.decode())
    return data.get("changeEntries", [])


def get_file_diff(
    org: str,
    project: str,
    repo: str,
    base_commit: str,
    target_commit: str,
    file_path: str,
    headers: dict
) -> dict:
    """Get the diff for a specific file between two commits."""
    # Get base version content
    base_content = get_file_content(org, project, repo, base_commit, file_path, headers)
    
    # Get target version content
    target_content = get_file_content(org, project, repo, target_commit, file_path, headers)
    
    return {
        "path": file_path,
        "baseContent": base_content,
        "targetContent": target_content
    }


def get_file_content(
    org: str,
    project: str,
    repo: str,
    commit: str,
    file_path: str,
    headers: dict
) -> Optional[str]:
    """Get file content at a specific commit."""
    # Remove leading slash if present
    clean_path = file_path.lstrip("/")
    
    url = (
        f"https://dev.azure.com/{org}/{project}/_apis/git/repositories/{repo}"
        f"/items?path={clean_path}&versionType=commit&version={commit}"
        f"&includeContent=true&api-version=7.1"
    )
    
    try:
        response = api_request(url, headers, accept="application/octet-stream")
        return response.decode("utf-8", errors="replace")
    except SystemExit:
        # File doesn't exist at this commit (could be new or deleted)
        return None


def get_commit_diffs(
    org: str,
    project: str,
    repo: str,
    base_commit: str,
    target_commit: str,
    headers: dict
) -> dict:
    """Get the diff between two commits."""
    url = (
        f"https://dev.azure.com/{org}/{project}/_apis/git/repositories/{repo}"
        f"/diffs/commits?baseVersion={base_commit}&targetVersion={target_commit}"
        f"&api-version=7.1"
    )
    response = api_request(url, headers)
    return json.loads(response.decode())


def format_change_type(change_type: str) -> str:
    """Format change type to human readable."""
    mapping = {
        "add": "Added",
        "edit": "Modified", 
        "delete": "Deleted",
        "rename": "Renamed",
        "sourceRename": "Renamed (source)",
        "targetRename": "Renamed (target)"
    }
    return mapping.get(change_type, change_type)


def main():
    parser = argparse.ArgumentParser(description="Get PR diff and changed files")
    parser.add_argument("--org", required=True, help="Azure DevOps organization name")
    parser.add_argument("--project", required=True, help="Azure DevOps project name")
    parser.add_argument("--repo", required=True, help="Repository name")
    parser.add_argument("--pr-id", required=True, type=int, help="Pull request ID")
    parser.add_argument("--file", help="Specific file path to get diff for (optional)")
    parser.add_argument("--include-content", action="store_true", 
                        help="Include full file content (can be large)")
    
    args = parser.parse_args()
    
    pat = os.environ.get("AZURE_DEVOPS_PAT")
    if not pat:
        print(json.dumps({"error": True, "message": "AZURE_DEVOPS_PAT environment variable not set"}))
        sys.exit(1)
    
    headers = get_auth_header(pat)
    
    # Get PR details
    pr = get_pr_details(args.org, args.project, args.repo, args.pr_id, headers)
    
    source_branch = pr.get("sourceRefName", "").replace("refs/heads/", "")
    target_branch = pr.get("targetRefName", "").replace("refs/heads/", "")
    last_merge_source_commit = pr.get("lastMergeSourceCommit", {}).get("commitId")
    last_merge_target_commit = pr.get("lastMergeTargetCommit", {}).get("commitId")
    
    # Get iterations to find changes
    iterations = get_pr_iterations(args.org, args.project, args.repo, args.pr_id, headers)
    
    if not iterations:
        print(json.dumps({
            "error": True,
            "message": "No iterations found for this PR"
        }))
        sys.exit(1)
    
    # Get the latest iteration
    latest_iteration = iterations[-1]
    iteration_id = latest_iteration.get("id")
    
    # Get changes from latest iteration
    changes = get_iteration_changes(
        args.org, args.project, args.repo, args.pr_id, iteration_id, headers
    )
    
    # Get commit diff summary
    diff_summary = None
    if last_merge_source_commit and last_merge_target_commit:
        diff_summary = get_commit_diffs(
            args.org, args.project, args.repo,
            last_merge_target_commit, last_merge_source_commit, headers
        )
    
    # Format changed files
    changed_files = []
    for change in changes:
        item = change.get("item", {})
        file_path = item.get("path", "")
        change_type = change.get("changeType", "unknown")
        
        file_info = {
            "path": file_path,
            "changeType": format_change_type(change_type),
            "originalPath": item.get("originalObjectId")  # For renames
        }
        
        # If specific file requested or include-content flag, get the content
        if args.include_content or (args.file and file_path == args.file):
            if last_merge_source_commit:
                file_info["content"] = get_file_content(
                    args.org, args.project, args.repo,
                    last_merge_source_commit, file_path, headers
                )
            if last_merge_target_commit and change_type in ["edit", "delete"]:
                file_info["originalContent"] = get_file_content(
                    args.org, args.project, args.repo,
                    last_merge_target_commit, file_path, headers
                )
        
        changed_files.append(file_info)
    
    # If specific file requested, filter to just that file
    if args.file:
        changed_files = [f for f in changed_files if f["path"] == args.file]
        if not changed_files:
            print(json.dumps({
                "error": True,
                "message": f"File {args.file} not found in PR changes"
            }))
            sys.exit(1)
    
    result = {
        "pullRequest": {
            "id": pr.get("pullRequestId"),
            "title": pr.get("title"),
            "description": pr.get("description", ""),
            "author": pr.get("createdBy", {}).get("displayName"),
            "sourceBranch": source_branch,
            "targetBranch": target_branch,
            "status": pr.get("status"),
            "isDraft": pr.get("isDraft", False)
        },
        "commits": {
            "source": last_merge_source_commit,
            "target": last_merge_target_commit
        },
        "summary": {
            "totalFiles": len(changed_files),
            "additions": diff_summary.get("aheadCount", 0) if diff_summary else 0,
            "deletions": diff_summary.get("behindCount", 0) if diff_summary else 0
        },
        "changedFiles": changed_files
    }
    
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

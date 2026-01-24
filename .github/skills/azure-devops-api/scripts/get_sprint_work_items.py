#!/usr/bin/env python3
"""
Query work items from the current sprint board for a team.

Uses the Azure DevOps REST API to:
1. Get the current iteration for a team
2. Query work items in that iteration filtered by area path

Requires AZURE_DEVOPS_PAT environment variable with Work Items (Read) scope.

Usage:
    python get_sprint_work_items.py --org <org> --project <project> --team <team> [options]

Examples:
    # Get unassigned items in current sprint (for picking up work)
    python get_sprint_work_items.py --org contoso --project payments --team "Platform Team" --unassigned

    # Get all items in current sprint
    python get_sprint_work_items.py --org contoso --project payments --team "Platform Team"

    # Get in-progress items (to check on colleagues)
    python get_sprint_work_items.py --org contoso --project payments --team "Platform Team" --state "In Progress"

    # Get items assigned to a specific user
    python get_sprint_work_items.py --org contoso --project payments --team "Platform Team" --assigned-to "user@example.com"
"""

import argparse
import json
import os
import sys
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime


def get_auth_header(pat: str) -> dict:
    """Create authorization header from PAT."""
    import base64
    token = base64.b64encode(f":{pat}".encode()).decode()
    return {"Authorization": f"Basic {token}"}


def api_request(url: str, headers: dict) -> dict:
    """Make an API request and return JSON response."""
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as e:
        error_body = e.read().decode() if e.fp else ""
        return {"error": True, "status": e.code, "message": str(e), "details": error_body}
    except urllib.error.URLError as e:
        return {"error": True, "status": 0, "message": str(e), "details": ""}


def api_post(url: str, headers: dict, body: dict) -> dict:
    """Make a POST request and return JSON response."""
    req_headers = {**headers, "Content-Type": "application/json"}
    data = json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, headers=req_headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as e:
        error_body = e.read().decode() if e.fp else ""
        return {"error": True, "status": e.code, "message": str(e), "details": error_body}
    except urllib.error.URLError as e:
        return {"error": True, "status": 0, "message": str(e), "details": ""}


def get_current_iteration(org: str, project: str, team: str, headers: dict) -> dict | None:
    """Get the current iteration for a team."""
    # URL encode the team name for the path
    team_encoded = urllib.parse.quote(team)
    url = f"https://dev.azure.com/{org}/{project}/{team_encoded}/_apis/work/teamsettings/iterations?$timeframe=current&api-version=7.1"
    
    result = api_request(url, headers)
    
    if result.get("error"):
        return None
    
    iterations = result.get("value", [])
    if iterations:
        return iterations[0]  # Current iteration
    return None


def query_work_items(
    org: str,
    project: str,
    team: str,
    iteration_path: str,
    headers: dict,
    states: list[str] | None = None,
    unassigned: bool = False,
    assigned_to: str | None = None,
    work_item_types: list[str] | None = None,
) -> list[dict]:
    """Query work items using WIQL."""
    
    # Build the area path filter: {Project}\{Team}
    area_path = f"{project}\\{team}"
    
    # Default work item types
    if not work_item_types:
        work_item_types = ["Product Backlog Item", "Spike"]
    
    types_clause = ", ".join(f"'{t}'" for t in work_item_types)
    
    # Build WHERE clauses
    where_clauses = [
        f"[System.TeamProject] = '{project}'",
        f"[System.AreaPath] UNDER '{area_path}'",
        f"[System.IterationPath] = '{iteration_path}'",
        f"[System.WorkItemType] IN ({types_clause})",
    ]
    
    if states:
        states_clause = ", ".join(f"'{s}'" for s in states)
        where_clauses.append(f"[System.State] IN ({states_clause})")
    
    if unassigned:
        where_clauses.append("([System.AssignedTo] = '' OR [System.AssignedTo] IS NULL)")
    elif assigned_to:
        where_clauses.append(f"[System.AssignedTo] = '{assigned_to}'")
    
    wiql = f"""
        SELECT [System.Id], [System.Title], [System.State], [System.WorkItemType],
               [System.AssignedTo], [Microsoft.VSTS.Scheduling.Effort],
               [Microsoft.VSTS.Common.BacklogPriority], [System.ChangedDate]
        FROM WorkItems
        WHERE {' AND '.join(where_clauses)}
        ORDER BY [Microsoft.VSTS.Common.BacklogPriority] ASC
    """
    
    # Execute WIQL query
    url = f"https://dev.azure.com/{org}/{project}/_apis/wit/wiql?api-version=7.1"
    result = api_post(url, headers, {"query": wiql})
    
    if result.get("error"):
        return []
    
    work_item_refs = result.get("workItems", [])
    if not work_item_refs:
        return []
    
    # Get work item details in batches (max 200 per request)
    ids = [wi["id"] for wi in work_item_refs]
    work_items = []
    
    fields = [
        "System.Id",
        "System.Title", 
        "System.State",
        "System.WorkItemType",
        "System.AssignedTo",
        "Microsoft.VSTS.Scheduling.Effort",
        "Microsoft.VSTS.Common.BacklogPriority",
        "System.ChangedDate",
    ]
    
    for i in range(0, len(ids), 200):
        batch_ids = ids[i:i+200]
        ids_param = ",".join(str(id) for id in batch_ids)
        fields_param = ",".join(fields)
        
        batch_url = f"https://dev.azure.com/{org}/{project}/_apis/wit/workitems?ids={ids_param}&fields={fields_param}&api-version=7.1"
        batch_result = api_request(batch_url, headers)
        
        if not batch_result.get("error"):
            work_items.extend(batch_result.get("value", []))
    
    return work_items


def format_work_item(wi: dict, org: str, project: str) -> dict:
    """Format a work item for output."""
    fields = wi.get("fields", {})
    wi_id = wi.get("id")
    
    # Parse assigned to
    assigned_to = fields.get("System.AssignedTo", {})
    if isinstance(assigned_to, dict):
        assigned_name = assigned_to.get("displayName", "Unassigned")
    else:
        assigned_name = assigned_to if assigned_to else "Unassigned"
    
    # Calculate days since last change
    changed_date_str = fields.get("System.ChangedDate", "")
    days_since_change = None
    if changed_date_str:
        try:
            # Parse ISO format date
            changed_date = datetime.fromisoformat(changed_date_str.replace("Z", "+00:00"))
            days_since_change = (datetime.now(changed_date.tzinfo) - changed_date).days
        except (ValueError, TypeError):
            pass
    
    return {
        "id": wi_id,
        "type": fields.get("System.WorkItemType", ""),
        "title": fields.get("System.Title", ""),
        "state": fields.get("System.State", ""),
        "assignedTo": assigned_name,
        "effort": fields.get("Microsoft.VSTS.Scheduling.Effort"),
        "priority": fields.get("Microsoft.VSTS.Common.BacklogPriority"),
        "daysSinceChange": days_since_change,
        "webUrl": f"https://dev.azure.com/{org}/{project}/_workitems/edit/{wi_id}",
    }


def main():
    parser = argparse.ArgumentParser(
        description="Query work items from the current sprint board"
    )
    parser.add_argument("--org", required=True, help="Azure DevOps organization name")
    parser.add_argument("--project", required=True, help="Azure DevOps project name")
    parser.add_argument("--team", required=True, help="Team name (case-sensitive)")
    parser.add_argument(
        "--state",
        action="append",
        help="Filter by state (can be specified multiple times)",
    )
    parser.add_argument(
        "--unassigned",
        action="store_true",
        help="Only return unassigned work items",
    )
    parser.add_argument(
        "--assigned-to",
        help="Filter by assigned user (email or display name)",
    )
    parser.add_argument(
        "--type",
        action="append",
        dest="work_item_types",
        help="Work item types to include (default: 'Product Backlog Item', 'Spike')",
    )
    
    args = parser.parse_args()
    
    # Get PAT from environment
    pat = os.environ.get("AZURE_DEVOPS_PAT")
    if not pat:
        print(json.dumps({
            "error": True,
            "message": "AZURE_DEVOPS_PAT environment variable not set",
            "details": "Set the PAT in .vscode/settings.json terminal.integrated.env.*"
        }))
        sys.exit(1)
    
    headers = get_auth_header(pat)
    
    # Get current iteration
    iteration = get_current_iteration(args.org, args.project, args.team, headers)
    
    if not iteration:
        print(json.dumps({
            "error": True,
            "message": f"Could not find current iteration for team '{args.team}'",
            "details": "Check that the team name is correct (case-sensitive) and has iterations configured",
        }))
        sys.exit(1)
    
    iteration_path = iteration.get("path", "")
    iteration_name = iteration.get("name", "")
    
    # Query work items
    work_items = query_work_items(
        org=args.org,
        project=args.project,
        team=args.team,
        iteration_path=iteration_path,
        headers=headers,
        states=args.state,
        unassigned=args.unassigned,
        assigned_to=args.assigned_to,
        work_item_types=args.work_item_types,
    )
    
    # Format output
    formatted_items = [
        format_work_item(wi, args.org, args.project)
        for wi in work_items
    ]
    
    output = {
        "iteration": {
            "name": iteration_name,
            "path": iteration_path,
        },
        "team": args.team,
        "areaPath": f"{args.project}\\{args.team}",
        "count": len(formatted_items),
        "workItems": formatted_items,
    }
    
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()

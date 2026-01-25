#!/usr/bin/env python3
"""
Query work items from the current sprint board for a team.
Uses Azure DevOps REST API to filter by Area Path and Iteration Path.
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


def api_request(url, headers):
    try:
        req = Request(url, headers=headers)
        with urlopen(req) as response:
            return json.loads(response.read().decode()), None
    except HTTPError as e:
        return None, {"error": True, "status": e.code, "message": e.reason}


def get_current_iteration(org, project, team, headers):
    url = f"https://dev.azure.com/{org}/{project}/{team}/_apis/work/teamsettings/iterations?$timeframe=current&api-version=7.1"
    data, err = api_request(url, headers)
    if err:
        return None, err
    iterations = data.get("value", [])
    if not iterations:
        return None, {"error": True, "message": "No current iteration found"}
    return iterations[0], None


def query_work_items(org, project, wiql, headers):
    url = f"https://dev.azure.com/{org}/{project}/_apis/wit/wiql?api-version=7.1"
    body = json.dumps({"query": wiql}).encode()
    try:
        req = Request(url, data=body, headers={**headers, "Content-Type": "application/json"})
        with urlopen(req) as response:
            return json.loads(response.read().decode()), None
    except HTTPError as e:
        return None, {"error": True, "status": e.code, "message": e.reason}


def get_work_items_batch(org, project, ids, headers):
    if not ids:
        return [], None
    url = f"https://dev.azure.com/{org}/{project}/_apis/wit/workitemsbatch?api-version=7.1"
    body = json.dumps({
        "ids": ids,
        "fields": ["System.Id", "System.WorkItemType", "System.Title", "System.State",
                   "System.AssignedTo", "Microsoft.VSTS.Scheduling.Effort",
                   "Microsoft.VSTS.Common.Priority", "System.ChangedDate"]
    }).encode()
    try:
        req = Request(url, data=body, headers={**headers, "Content-Type": "application/json"}, method="POST")
        with urlopen(req) as response:
            return json.loads(response.read().decode()).get("value", []), None
    except HTTPError as e:
        return None, {"error": True, "status": e.code, "message": e.reason}


def main():
    parser = argparse.ArgumentParser(description="Get sprint work items for a team")
    parser.add_argument("--org", required=True, help="Azure DevOps organization")
    parser.add_argument("--project", required=True, help="Project name")
    parser.add_argument("--team", required=True, help="Team name (case-sensitive)")
    parser.add_argument("--state", action="append", help="Filter by state (can repeat)")
    parser.add_argument("--unassigned", action="store_true", help="Only unassigned items")
    parser.add_argument("--assigned-to", help="Filter by assignee (@me or email)")
    parser.add_argument("--type", action="append", default=["Product Backlog Item", "Spike"],
                        help="Work item types")
    args = parser.parse_args()

    headers, err = get_auth_header()
    if err:
        print(json.dumps({"error": True, "message": err}))
        sys.exit(1)

    iteration, err = get_current_iteration(args.org, args.project, args.team, headers)
    if err:
        print(json.dumps(err))
        sys.exit(1)

    area_path = f"{args.project}\\{args.team}"
    iteration_path = iteration["path"]

    # Build WIQL query
    type_filter = " OR ".join([f"[System.WorkItemType] = '{t}'" for t in args.type])
    wiql = f"""
    SELECT [System.Id]
    FROM WorkItems
    WHERE ({type_filter})
      AND [System.AreaPath] UNDER '{area_path}'
      AND [System.IterationPath] = '{iteration_path}'
    """

    if args.unassigned:
        wiql += " AND [System.AssignedTo] = ''"
    elif args.assigned_to:
        if args.assigned_to == "@me":
            wiql += " AND [System.AssignedTo] = @me"
        else:
            wiql += f" AND [System.AssignedTo] = '{args.assigned_to}'"

    if args.state:
        state_filter = " OR ".join([f"[System.State] = '{s}'" for s in args.state])
        wiql += f" AND ({state_filter})"

    wiql += " ORDER BY [Microsoft.VSTS.Common.Priority] ASC, [System.ChangedDate] DESC"

    result, err = query_work_items(args.org, args.project, wiql, headers)
    if err:
        print(json.dumps(err))
        sys.exit(1)

    ids = [item["id"] for item in result.get("workItems", [])]
    work_items, err = get_work_items_batch(args.org, args.project, ids, headers)
    if err:
        print(json.dumps(err))
        sys.exit(1)

    now = datetime.utcnow()
    output = {
        "iteration": {"name": iteration["name"], "path": iteration_path},
        "team": args.team,
        "areaPath": area_path,
        "count": len(work_items),
        "workItems": []
    }

    for wi in work_items:
        fields = wi.get("fields", {})
        changed = datetime.fromisoformat(fields.get("System.ChangedDate", "").replace("Z", "+00:00"))
        days_since = (now - changed.replace(tzinfo=None)).days

        output["workItems"].append({
            "id": wi["id"],
            "type": fields.get("System.WorkItemType"),
            "title": fields.get("System.Title"),
            "state": fields.get("System.State"),
            "assignedTo": fields.get("System.AssignedTo", {}).get("displayName", "Unassigned"),
            "effort": fields.get("Microsoft.VSTS.Scheduling.Effort"),
            "priority": fields.get("Microsoft.VSTS.Common.Priority"),
            "daysSinceChange": days_since,
            "webUrl": f"https://dev.azure.com/{args.org}/{args.project}/_workitems/edit/{wi['id']}"
        })

    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()

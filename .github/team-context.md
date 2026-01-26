# Team Context

Shared configuration for Azure DevOps and team settings. This file is shared across repositories.

## Azure DevOps

- **Organization:** {your-org}
- **Project:** {your-project}

## Team

- **Team name:** {Your Team Name}
- **Team ID:** {team-guid-for-pr-queries}
- **Area Path:** {Project}\\{Team}

## User

- **User ID:** {your-user-guid}

The User ID is used to exclude your own PRs from review lists. Find it in Azure DevOps by inspecting network requests or using the API.

## Finding These Values

**Organization and Project:** From your Azure DevOps URL: `dev.azure.com/{organization}/{project}`

**Team name:** Project Settings → Teams (case-sensitive, must match exactly)

**Team ID:** Navigate to your team's settings page — the GUID is in the URL, or use:

```bash
az devops team list --organization https://dev.azure.com/{org} --project {project} --output table
```

**User ID:** Use the Azure DevOps API or inspect network requests when viewing your profile.

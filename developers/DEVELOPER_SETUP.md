# Agent Workflow Setup Guide

This guide helps developers set up and use the GitHub Copilot agent workflow for Azure DevOps-driven development.

## Prerequisites

Before starting, ensure you have:

- **VS Code** with GitHub Copilot extension installed
- **GitHub Copilot subscription** (Pro, Pro+, Business, or Enterprise)
- **Node.js 18+** installed (for the MCP server)
- **Azure CLI** installed and authenticated (`az login`)
- **Git** configured with credentials for your Azure DevOps repositories

## Quick Start

### 1. Copy the Configuration Files

Copy the following directories and files to your repository:

```
.github/
├── copilot-instructions.md
├── project-context.md              # Template—customise for your repo
├── agents/
│   ├── what-next.agent.md          # Entry point
│   ├── pipeline-investigator.agent.md
│   ├── work-item-pickup.agent.md
│   ├── planner.agent.md
│   ├── tdd-coder.agent.md
│   ├── one-shot-coder.agent.md
│   ├── reviewer.agent.md
│   ├── committer.agent.md
│   └── pr-creator.agent.md
└── skills/
    ├── azure-devops-workflow/
    │   └── SKILL.md
    ├── azure-devops-api/           # Script for team PR queries
    │   ├── SKILL.md
    │   └── scripts/
    │       └── get_team_prs.py
    └── vertical-slice-architecture/
        └── SKILL.md                # Only for VSA repos

.vscode/
├── mcp.json
└── settings.template.json          # Copy to settings.json and add your PAT
```

### 2. Configure the MCP Server

Edit `.vscode/mcp.json` if you need to adjust the Azure DevOps organisation name. The file will prompt you for this when the server starts.

### 3. Add entries to .gitignore

The workflow creates planning files and uses local settings that shouldn't be committed:

```bash
echo ".planning/" >> .gitignore
echo ".vscode/settings.json" >> .gitignore
```

### 4. Configure Project Context

Edit `.github/project-context.md` to configure your team and repository settings. This is **required** for most workflow features.

**Required fields:**

| Field        | Purpose                | Where to Find                                         |
| ------------ | ---------------------- | ----------------------------------------------------- |
| Organization | Azure DevOps API calls | Your Azure DevOps URL: `dev.azure.com/{organization}` |
| Project      | Azure DevOps API calls | Your project name in Azure DevOps                     |
| Team name    | Sprint board queries   | Project Settings > Teams (case-sensitive)             |
| Team ID      | PR filtering           | Team settings URL contains the GUID                   |

**Optional fields:**

- Architecture pattern (e.g., VSA) — enables pattern-specific guidance
- Testing conventions
- Domain context

See the template in `.github/project-context.md` for all available options.

### 5. Verify Team Configuration

The **team name** must exactly match your Azure DevOps team name (case-sensitive). This is used for:

- Querying the current sprint board (`@CurrentIteration` in WIQL)
- Finding in-progress work for colleagues
- Filtering available work items

To find your team name: Azure DevOps > Project Settings > Teams

### 6. Start the MCP Server

1. Open VS Code in your repository
2. Open the Command Palette (Ctrl+Shift+P / Cmd+Shift+P)
3. Run "MCP: Start Server"
4. Select "azure-devops" when prompted
5. Enter your Azure DevOps organisation name

Verify the server is running in the MCP panel (View → MCP).

### 7. Configure Azure DevOps PAT for Scripts

Some features (PR diffs, team-filtered PR lists) require the `azure-devops-api` skill scripts, which need a Personal Access Token.

**Step 1: Create a PAT in Azure DevOps**

1. Go to Azure DevOps → User Settings → Personal Access Tokens
2. Create a new token with these scopes:
   - **Code:** Read
   - **Work Items:** Read
   - **Build:** Read (for pipeline status)
3. Copy the token (you won't see it again)

**Step 2: Configure VS Code to provide the PAT**

Add the PAT to your VS Code workspace settings. Create or edit `.vscode/settings.json`:

```json
{
  "terminal.integrated.env.linux": {
    "AZURE_DEVOPS_PAT": "your-pat-here"
  },
  "terminal.integrated.env.osx": {
    "AZURE_DEVOPS_PAT": "your-pat-here"
  },
  "terminal.integrated.env.windows": {
    "AZURE_DEVOPS_PAT": "your-pat-here"
  }
}
```

**Step 3: Ensure the PAT isn't committed**

Add to `.gitignore`:

```
# VS Code settings may contain secrets
.vscode/settings.json
```

If you need to share other VS Code settings with the team, use `.vscode/settings.template.json` (without the PAT) and have developers copy it locally.

**Step 4: Restart VS Code**

Close and reopen VS Code (or reload the window) for the environment variable to take effect.

**Verify it works:**

Open a new terminal in VS Code and run:

```bash
# Linux/macOS
echo $AZURE_DEVOPS_PAT

# Windows PowerShell
echo $env:AZURE_DEVOPS_PAT
```

You should see your PAT (or at least confirm it's set).

### 8. Verify Azure CLI Authentication

The MCP server uses your Azure CLI credentials:

```bash
az account show
```

If not logged in:

```bash
az login
```

## Using the Workflow

### Starting Your Day: What's Next?

The workflow starts with the **What's Next** agent, which helps you prioritise:

1. Open GitHub Copilot Chat in VS Code
2. Select the **What's Next** agent from the agents dropdown
3. Ask what you should work on:

   ```
   What should I work on next?
   ```

The agent checks (in priority order):

- PRs awaiting your team's review (with links to review manually)
- Failing pipelines
- Colleagues who might need help (work items stuck too long)
- Your own in-progress work
- New work items to pick up

Only after confirming higher-priority items don't need attention will it suggest picking up new work.

### Investigating a Pipeline Failure

If the What's Next agent surfaces failing pipelines, hand off to the **Pipeline Investigator** agent:

1. Click the "Investigate Pipeline Failure" handoff, or
2. Select the Pipeline Investigator agent and specify which pipeline to investigate

### Picking Up a Work Item

1. Open GitHub Copilot Chat in VS Code
2. Select the **Work Item Pickup** agent from the agents dropdown
3. Ask to pick up a work item:

   ```
   Pick up work item 12345
   ```

The agent will:

- Fetch and validate the work item
- Check for incomplete predecessors
- Assign it to you and move to In Progress
- Create a feature branch
- Summarise the work item

### Creating a Plan

After pickup, hand off to the **Planner** agent:

1. Click the "Plan Implementation" handoff button, or
2. Select the Planner agent and ask it to create a plan

The planner will:

- Analyse the codebase
- Create a checklist in `.planning/PLAN.md`
- Identify test scenarios for each item

Review the plan before proceeding. You can ask for adjustments.

### Implementing (TDD Path)

For complex or risky changes, use the iterative TDD approach:

1. Select **TDD Coder** agent
2. It implements one checklist item at a time
3. After each item, hand off to **Reviewer**
4. Address any feedback
5. Hand off to **Committer**
6. Repeat for next item

Each checklist item gets its own reviewed, tested commit.

### Implementing (One-Shot Path)

For small, well-defined changes:

1. Select **One-Shot Coder** agent
2. It implements all checklist items in one pass
3. Hand off to **Reviewer** once
4. Address feedback
5. Hand off to **Committer** for a single commit

### Creating a Pull Request

When all items are committed:

1. Select **PR Creator** agent (or use the handoff)
2. Ask it to create the PR:

   ```
   Create the pull request
   ```

The agent will:

- Push the branch
- Create a draft PR with template filled in
- Link to the work item
- Move work item to Awaiting Merge

## Workflow Modes

| Mode         | Best For                                        | Commits            | Review Cycles |
| ------------ | ----------------------------------------------- | ------------------ | ------------- |
| **TDD**      | Complex changes, risky areas, learning new code | Per checklist item | Per item      |
| **One-Shot** | Small changes, well-understood scope            | Single commit      | Once at end   |

Choose TDD when in doubt—the overhead is small compared to catching issues late.

## File Locations

| File/Directory                             | Purpose                                                         |
| ------------------------------------------ | --------------------------------------------------------------- |
| `.github/copilot-instructions.md`          | Global coding standards, applied to all agents                  |
| `.github/project-context.md`               | Repository-specific architecture, team, and Azure DevOps config |
| `.github/agents/*.agent.md`                | Custom agent definitions                                        |
| `.github/skills/*/SKILL.md`                | Reusable knowledge loaded on-demand                             |
| `.github/skills/azure-devops-api/scripts/` | Python scripts for Azure DevOps API access                      |
| `.vscode/mcp.json`                         | MCP server configuration                                        |
| `.vscode/settings.json`                    | VS Code settings including PAT (gitignored)                     |
| `.vscode/settings.template.json`           | Template for settings.json                                      |
| `.planning/PLAN.md`                        | Current implementation plan (gitignored)                        |

## Troubleshooting

### MCP Server Won't Start

1. Check Node.js is installed: `node --version` (need 18+)
2. Check the MCP panel in VS Code for errors
3. Try restarting VS Code

### Azure DevOps Authentication Fails

1. Verify Azure CLI login: `az account show`
2. Re-authenticate: `az login`
3. Ensure you have access to the Azure DevOps organisation

### Agent Not Finding Work Item

1. Check the work item ID is correct
2. Verify you have permission to view the work item
3. Ensure the MCP server is running and connected

### Skill Not Loading

Skills load automatically based on context. If a skill isn't being used:

1. Check the skill exists in `.github/skills/{name}/SKILL.md`
2. Verify the YAML frontmatter has `name` and `description`
3. Try explicitly mentioning the skill's domain in your prompt

### Plan Not Found by Coder

The coder agents expect `.planning/PLAN.md` to exist:

1. Ensure you ran the Planner first
2. Check the file was created in the repository root
3. Verify the `.planning/` directory exists

## Customising the Workflow

### Adjusting Coding Standards

Edit `.github/copilot-instructions.md` to change:

- C# conventions
- Testing philosophy
- Commit message format
- Banking domain constraints

### Adding New Skills

Create a new skill in `.github/skills/{skill-name}/SKILL.md`:

```yaml
---
name: skill-name
description: "When to use this skill. Be specific about triggers."
---
# Skill Title

Your detailed instructions here...
```

### Modifying Agents

Agent files are in `.github/agents/`. Each has:

- YAML frontmatter (name, description, tools, handoffs)
- Markdown body (instructions)

See the existing agents for examples.

### Changing Work Item States

If your Azure DevOps board uses different state names, update:

1. `.github/skills/azure-devops-workflow/SKILL.md` — State definitions
2. Agents that reference specific states (work-item-pickup, pr-creator)

## Team Rollout Checklist

When rolling out to your team:

- [ ] Copy configuration files to shared repositories
- [ ] Add `.planning/` to `.gitignore`
- [ ] Verify MCP server works for each team member
- [ ] Ensure everyone has Azure CLI configured
- [ ] Review and adjust coding standards in `copilot-instructions.md`
- [ ] Walk through the workflow with one real work item
- [ ] Collect feedback and iterate

## Quick Reference

### Agent Workflow

```
what-next (entry point)
    ├── PRs awaiting review → (review manually in Azure DevOps)
    ├── Failing pipelines → pipeline-investigator
    ├── Colleagues need help → (informational, reach out manually)
    ├── Your in-progress work → planner / coder (resume)
    └── Nothing urgent → work-item-pickup

work-item-pickup → planner → [coder → reviewer → committer] → pr-creator
```

### Handoff Shortcuts

| From                  | To                    | When                           |
| --------------------- | --------------------- | ------------------------------ |
| what-next             | pipeline-investigator | Failing pipelines              |
| what-next             | planner               | Resume in-progress work        |
| what-next             | work-item-pickup      | Ready for new work             |
| work-item-pickup      | planner               | After branch created           |
| planner               | tdd-coder             | Ready to implement (iterative) |
| planner               | one-shot-coder        | Ready to implement (batch)     |
| tdd-coder             | reviewer              | Item implemented               |
| one-shot-coder        | reviewer              | All items implemented          |
| reviewer              | tdd-coder             | Feedback to address            |
| reviewer              | one-shot-coder        | Feedback to address            |
| reviewer              | committer             | Approved                       |
| committer             | tdd-coder             | Next item (TDD only)           |
| committer             | pr-creator            | All items complete             |
| pipeline-investigator | what-next             | Investigation complete         |

### Branch Naming

```
backlog/{workitem_id}-{short-description}
```

### Commit Format

```
<type>(<scope>): <description>
```

Types: `feat`, `fix`, `test`, `refactor`, `docs`, `chore`

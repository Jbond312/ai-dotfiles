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
my-repo/
├── project-context.md              # Repo-specific (architecture, external deps)
└── .github/
    ├── CHANGELOG.md                # Version history
    ├── copilot-instructions.md     # Global workflow overview
    ├── instructions/               # Pattern-specific instructions (auto-apply)
    │   ├── banking.instructions.md # → Features/Domain/Infrastructure
    │   ├── csharp.instructions.md  # → All .cs files
    │   └── tests.instructions.md   # → Test files
    ├── agents/
    │   ├── what-next.agent.md      # Entry point
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
        ├── azure-devops-api/
        │   ├── SKILL.md
        │   └── scripts/
        │       ├── get_sprint_work_items.py
        │       └── get_team_prs.py
        ├── code-reviewing/
        │   └── SKILL.md
        ├── csharp-coding/
        │   └── SKILL.md
        ├── dotnet-testing/
        │   └── SKILL.md
        ├── git-committing/
        │   └── SKILL.md
        ├── known-issues/
        │   └── SKILL.md
        ├── repo-analyzer/
        │   └── SKILL.md
        └── vertical-slice-architecture/
            ├── SKILL.md
            └── reference/
                ├── code-review-checklist.md
                └── slice-components.md

.vscode/
├── mcp.json
└── settings.template.json          # Copy to settings.json and configure
```

### 2. Enable Agent Skills in VS Code

Agent Skills are in preview. Enable them in VS Code settings:

1. Open Settings (Ctrl+,)
2. Search for `chat.useAgentSkills`
3. Check the box to enable

### 3. Configure Azure DevOps Environment Variables

The Python scripts read Azure DevOps configuration from environment variables. Configure these in `.vscode/settings.json`:

```json
{
  "terminal.integrated.env.windows": {
    "AZURE_DEVOPS_PAT": "your-pat-here",
    "AZURE_DEVOPS_ORG": "your-org",
    "AZURE_DEVOPS_PROJECT": "your-project",
    "AZURE_DEVOPS_TEAM": "Your Team Name",
    "AZURE_DEVOPS_TEAM_ID": "team-guid-for-pr-queries",
    "AZURE_DEVOPS_USER_ID": "your-user-guid"
  },
  "terminal.integrated.env.osx": {
    "AZURE_DEVOPS_PAT": "your-pat-here",
    "AZURE_DEVOPS_ORG": "your-org",
    "AZURE_DEVOPS_PROJECT": "your-project",
    "AZURE_DEVOPS_TEAM": "Your Team Name",
    "AZURE_DEVOPS_TEAM_ID": "team-guid-for-pr-queries",
    "AZURE_DEVOPS_USER_ID": "your-user-guid"
  },
  "terminal.integrated.env.linux": {
    "AZURE_DEVOPS_PAT": "your-pat-here",
    "AZURE_DEVOPS_ORG": "your-org",
    "AZURE_DEVOPS_PROJECT": "your-project",
    "AZURE_DEVOPS_TEAM": "Your Team Name",
    "AZURE_DEVOPS_TEAM_ID": "team-guid-for-pr-queries",
    "AZURE_DEVOPS_USER_ID": "your-user-guid"
  }
}
```

**Required variables:**
| Variable | Purpose | Where to Find |
|----------|---------|---------------|
| `AZURE_DEVOPS_PAT` | Authentication | Azure DevOps > User Settings > Personal Access Tokens |
| `AZURE_DEVOPS_ORG` | API calls | Your Azure DevOps URL: `dev.azure.com/{organization}` |
| `AZURE_DEVOPS_PROJECT` | API calls | Your project name in Azure DevOps |
| `AZURE_DEVOPS_TEAM` | Sprint queries | Project Settings > Teams (case-sensitive) |

**Optional variables:**
| Variable | Purpose | Where to Find |
|----------|---------|---------------|
| `AZURE_DEVOPS_TEAM_ID` | PR filtering by team | Team settings URL contains the GUID |
| `AZURE_DEVOPS_USER_ID` | Exclude own PRs | Azure DevOps API or network inspection |

### 4. Add entries to .gitignore

The workflow creates planning files and uses local settings that shouldn't be committed:

```bash
# Local planning artifacts
echo ".planning/" >> .gitignore

# Local VS Code settings (contains PAT and env vars)
echo ".vscode/" >> .gitignore
```

**Note:** The agents will also check and add these entries automatically when you pick up a work item or create a plan, but it's good practice to add them upfront.

If you want to share some VS Code settings with your team while keeping secrets local, you can be more selective:

```bash
# Alternative: only ignore settings.json, share other .vscode files
echo ".vscode/settings.json" >> .gitignore
```

### 5. Configure Project Context (Per-Repo)

Create `project-context.md` at the **repository root** (not in `.github/`). This file is specific to each repository.

| Field                 | Purpose                                          |
| --------------------- | ------------------------------------------------ |
| Repository name       | Display purposes                                 |
| Architecture pattern  | Enables pattern-specific guidance (e.g., VSA)    |
| Key directories       | Helps agents navigate the codebase               |
| External dependencies | Documents stored procs, APIs for review flagging |

See the template in `project-context.md` for all available options.

### 6. Configure the MCP Server (Optional)

If you need Azure DevOps MCP for individual work item lookups:

1. Edit `.vscode/mcp.json` if you need to adjust the Azure DevOps organisation name
2. The server will prompt for this when it starts

### 7. Verify Setup

1. Open a new terminal in VS Code
2. Run a test query:

```bash
python .github/skills/azure-devops-api/scripts/get_sprint_work_items.py --unassigned
```

If configured correctly, you'll see JSON output with work items. If not, you'll see an error indicating which environment variable is missing.

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
- Your own in-progress work
- New work items to pick up (shows top 5)

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

| File/Directory                             | Purpose                                                            |
| ------------------------------------------ | ------------------------------------------------------------------ |
| `project-context.md`                       | Repo-specific config (architecture, external deps) — **repo root** |
| `.github/CHANGELOG.md`                     | Version history for the agent configuration                        |
| `.github/copilot-instructions.md`          | Global workflow overview, applied to all agents                    |
| `.github/instructions/*.instructions.md`   | Pattern-specific instructions (auto-apply based on `applyTo`)      |
| `.github/agents/*.agent.md`                | Custom agent definitions                                           |
| `.github/skills/*/SKILL.md`                | Reusable knowledge loaded on-demand                                |
| `.github/skills/*/reference/*.md`          | Detailed reference files for progressive disclosure                |
| `.github/skills/azure-devops-api/scripts/` | Python scripts for Azure DevOps API access                         |
| `.vscode/mcp.json`                         | MCP server configuration                                           |
| `.vscode/settings.json`                    | VS Code settings with Azure DevOps env vars (gitignored)           |
| `.vscode/settings.template.json`           | Template for settings.json                                         |
| `.planning/PLAN.md`                        | Current implementation plan (gitignored)                           |
| `.planning/CONVENTIONS.md`                 | Discovered repository coding conventions (gitignored)              |

## Troubleshooting

### Scripts Fail with "Environment Variable Not Set"

Check your `.vscode/settings.json` has all required variables:

- `AZURE_DEVOPS_PAT`
- `AZURE_DEVOPS_ORG`
- `AZURE_DEVOPS_PROJECT`
- `AZURE_DEVOPS_TEAM`

Restart VS Code after changing settings for environment variables to take effect.

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

The configuration uses a layered approach:

1. **Global instructions** (`.github/copilot-instructions.md`) — Workflow overview, branch naming, commit format references
2. **Pattern-specific instructions** (`.github/instructions/`) — Auto-apply based on file type:
   - `csharp.instructions.md` — C# conventions (all `.cs` files)
   - `tests.instructions.md` — Testing philosophy (test files)
   - `banking.instructions.md` — Domain constraints (Features/Domain/Infrastructure)
3. **Skills** (`.github/skills/`) — Loaded on-demand for specific tasks

To modify coding standards, edit the appropriate instruction file. Pattern-specific files only load when editing matching files, keeping context lean.

### Adding New Pattern-Specific Instructions

Create a new file in `.github/instructions/`:

```yaml
---
applyTo: "**/*.razor,**/*.cshtml"
description: "Blazor and Razor component conventions"
---
# Blazor Conventions

Your instructions here...
```

The `applyTo` field uses glob patterns. Multiple patterns can be separated with commas.

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

For larger skills, use progressive disclosure with reference files:

```
.github/skills/my-skill/
├── SKILL.md              # Overview (<100 lines ideally)
└── reference/
    ├── detailed-guide.md # Loaded only when needed
    └── examples.md       # Loaded only when needed
```

Reference files from SKILL.md with relative links: `See [reference/detailed-guide.md](reference/detailed-guide.md) for examples.`

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

- [ ] Copy `.github/` directory to shared repositories (agents, skills, instructions)
- [ ] Each developer configures `.vscode/settings.json` with Azure DevOps environment variables
- [ ] Create `project-context.md` at root of each repository
- [ ] Enable `chat.useAgentSkills` in VS Code settings
- [ ] Review pattern-specific instructions in `.github/instructions/` for your team's conventions
- [ ] Add `.planning/` and `.vscode/` to `.gitignore` (agents will also auto-add if missing)
- [ ] Ensure everyone has Azure CLI configured
- [ ] Run `repo-analyzer` skill once per repo to generate `.planning/CONVENTIONS.md`
- [ ] Walk through the workflow with one real work item
- [ ] Collect feedback and iterate

## Quick Reference

### Agent Workflow

```
what-next (entry point)
    ├── PRs awaiting review → (review manually in Azure DevOps)
    ├── Your in-progress work → planner / coder (resume)
    └── Available work → work-item-pickup

work-item-pickup → planner → [coder → reviewer → committer] → pr-creator
```

### Handoff Shortcuts

| From             | To               | When                           |
| ---------------- | ---------------- | ------------------------------ |
| what-next        | work-item-pickup | Ready for new work             |
| work-item-pickup | planner          | After branch created           |
| planner          | tdd-coder        | Ready to implement (iterative) |
| planner          | one-shot-coder   | Ready to implement (batch)     |
| tdd-coder        | reviewer         | Item implemented               |
| one-shot-coder   | reviewer         | All items implemented          |
| reviewer         | tdd-coder        | Feedback to address            |
| reviewer         | one-shot-coder   | Feedback to address            |
| reviewer         | committer        | Approved                       |
| committer        | tdd-coder        | Next item (TDD only)           |
| committer        | pr-creator       | All items complete             |

### Model Configuration

Agents are configured with appropriate models to balance capability and cost:

| Agent            | Model            | Rationale                             |
| ---------------- | ---------------- | ------------------------------------- |
| what-next        | claude-3-5-haiku | Light orchestration, simple decisions |
| work-item-pickup | claude-sonnet-4  | Predecessor checks, context gathering |
| planner          | claude-sonnet-4  | Codebase analysis, plan structuring   |
| tdd-coder        | claude-sonnet-4  | Code generation, test writing         |
| one-shot-coder   | claude-sonnet-4  | Code generation, test writing         |
| reviewer         | claude-sonnet-4  | Code review requires judgment         |
| committer        | claude-3-5-haiku | Template-based, simple task           |
| pr-creator       | claude-3-5-haiku | Template-based, simple task           |

**To change a model:** Edit the `model:` field in the agent's YAML frontmatter. Leave blank to use the model selected in the Copilot dropdown.

**Cost considerations:** Using Haiku for simple agents (committer, pr-creator, what-next) significantly reduces token usage without affecting quality, since these agents perform straightforward, template-based tasks.

### Branch Naming

```
backlog/{workitem_id}-{short-description}
```

### Commit Format

```
<type>(<scope>): <description>
```

Types: `feat`, `fix`, `test`, `refactor`, `docs`, `chore`

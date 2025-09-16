# Agent Context Documentation

This directory contains all documentation and tools specifically for AI agents working on GeoExhibit development.

## Documentation Files

### Core Architecture & Context
- **`AGENTS.md`** - Complete technical architecture overview and steel thread documentation
- **`PROJECT_STATUS.md`** - Current completion status and quality metrics
- **`DECISIONS.md`** - 13 numbered implementation decisions with rationale and commit links

### Development Workflow
- **`PLAYBOOK.md`** - Agent workflow guide for GitHub API integration
- **`ROADMAP.md`** - Development phases and GitHub issues dependency chain

### API Tools
- **`agent_playbook/`** - GitHub API helper scripts and automation tools
  - `gh_api.sh` - Core GitHub REST API wrapper
  - `issue_create.sh` - Create GitHub issues
  - `pr_create.sh` - Create pull requests
  - `pr_comment.sh` - Manage PR comments
  - `branch_create.sh` - Create feature branches
  - `Makefile` - Convenient command wrappers

## Quick Agent Onboarding

1. **Read AGENTS.md first** - Contains complete technical context
2. **Check PROJECT_STATUS.md** - Understand current completion state
3. **Review DECISIONS.md** - Understand key architectural choices
4. **Use PLAYBOOK.md** - For GitHub workflow guidance
5. **Reference ROADMAP.md** - For future development phases

## Usage

### For New Agents
```bash
# Start here for complete project understanding
cat docs/agent-context/AGENTS.md

# Check current status
cat docs/agent-context/PROJECT_STATUS.md

# Understand key decisions
cat docs/agent-context/DECISIONS.md
```

### For GitHub Integration
```bash
# Set up GitHub API access
export GH_TOKEN="your_github_token"
export GH_REPO="burrbd/geoexhibit"

# Use helper scripts
docs/agent-context/agent_playbook/gh_api.sh GET "/issues"
```

## Design Principles

This documentation follows GeoExhibit's minimalism principle:
- **Self-documenting**: Code structure and naming reduce need for comments
- **Decision-driven**: Major choices are numbered and rationale is provided
- **Context-rich**: Agents get complete picture quickly
- **Workflow-oriented**: Practical guidance for GitHub development

## Maintenance

When making significant changes to GeoExhibit:
1. Update relevant documentation in this directory
2. Add new decisions to DECISIONS.md with rationale
3. Update PROJECT_STATUS.md completion metrics
4. Keep AGENTS.md architecture overview current
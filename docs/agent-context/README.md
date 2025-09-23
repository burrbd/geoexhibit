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

## 🚀 **AGENT ONBOARDING (START HERE)**

**New agents MUST read this document first:**
```
📖 AGENTS.md - Complete agent guide with architecture, methodology, and setup
```

This single comprehensive guide covers:
- What GeoExhibit is (publish + exhibit workflow)
- Technical architecture and component overview
- Development methodology (London School TDD, SOLID principles)
- Environment setup and critical implementation notes
- GitHub workflow and API tools
- Testing strategy and common pitfalls
- Steel thread documentation (web map data flow)

## Supporting Context Documents

Reference these for specific needs:

1. **`PROJECT_STATUS.md`** - Current completion status and quality metrics  
2. **`DECISIONS.md`** - Numbered implementation decisions with rationale
3. **`PLAYBOOK.md`** - Detailed GitHub API workflow examples
4. **`ROADMAP.md`** - Development phases and issue dependencies

## Usage

### For New Agents
```bash
# Start here for complete project understanding (single comprehensive guide)
cat docs/agent-context/AGENTS.md

# Then reference these for specific context:
cat docs/agent-context/PROJECT_STATUS.md  # Current completion state
cat docs/agent-context/DECISIONS.md       # Implementation decisions
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
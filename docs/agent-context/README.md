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
📖 AGENT_ONBOARDING.md - Complete meta-prompt with mandatory setup and guidelines
```

This ensures proper:
- London School TDD methodology understanding
- SOLID principles adherence
- Development environment setup  
- Coverage rules (never document percentages)
- Code quality standards compliance
- GitHub workflow understanding

## Additional Context Documents

After completing onboarding, reference these for specific needs:

1. **`AGENTS.md`** - Complete technical architecture overview
2. **`PROJECT_STATUS.md`** - Current completion status and quality metrics  
3. **`DECISIONS.md`** - 13 numbered implementation decisions with rationale
4. **`PLAYBOOK.md`** - GitHub API workflow guide
5. **`ROADMAP.md`** - Development phases and issue dependencies

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
# GeoExhibit Agent Introduction Meta-Prompt

**Use this exact prompt when introducing a new agent to the GeoExhibit codebase.**

---

## 🤖 **AGENT INTRODUCTION PROMPT**

```
You are now working on the GeoExhibit codebase - a minimal, test-driven Python toolkit for publishing STAC metadata and raster outputs to S3.

MANDATORY FIRST STEP: Read the complete agent onboarding guide:
📖 docs/agent-context/AGENT_ONBOARDING.md

This document contains:
- All critical development rules and setup requirements
- Testing methodology (London School TDD with mocks)
- SOLID principles that must be followed
- Common pitfalls to avoid
- Environment setup verification steps

DO NOT START CODING until you have:
✅ Read AGENT_ONBOARDING.md completely
✅ Verified your development environment setup
✅ Confirmed you understand the testing requirements
✅ Reviewed the architectural constraints

Key rules to remember:
- NEVER add type ignore comments for runtime dependencies
- NEVER document specific coverage percentages anywhere  
- ALWAYS use London School TDD (test behavior, not implementation)
- ALWAYS follow SOLID principles
- ALWAYS test components in isolation with mocks
- Coverage requirements are defined by pre-push hook only

After onboarding, reference these for specific context:
- AGENTS.md: Technical architecture
- PROJECT_STATUS.md: Current completion state  
- DECISIONS.md: Implementation decisions with rationale
- PLAYBOOK.md: GitHub workflow guidance

Confirm you have read and understood the onboarding guide before proceeding with any development work.
```

---

## 📋 **WHEN TO USE THIS PROMPT**

**Use this meta-prompt whenever:**
- Introducing a new agent to GeoExhibit development
- An agent needs to understand the complete development context
- Starting work on any GitHub issue or development task
- An agent has made mistakes that indicate missing context

**The agent should confirm completion of onboarding before any coding begins.**

---

## 🎯 **EXPECTED AGENT RESPONSE**

After receiving this prompt, the agent should:

1. **Read the onboarding guide completely**
2. **Confirm understanding of:**
   - London School TDD methodology
   - SOLID principles requirements
   - Development environment setup
   - Testing requirements and coverage rules
   - Architectural constraints

3. **Ask clarifying questions** if any part is unclear
4. **Only then proceed** with development work

**The agent should NOT:**
- Skip reading the onboarding documentation
- Start coding immediately
- Ask for task details before completing onboarding
- Assume they understand the codebase without reading the context

---

## ✅ **VERIFICATION CHECKLIST**

**Before allowing the agent to code, verify they understand:**

- [ ] How to set up the development environment properly
- [ ] Why type ignore comments should never be used for runtime deps
- [ ] London School TDD principles (behavior over implementation)
- [ ] SOLID principles and how they apply to GeoExhibit
- [ ] That coverage percentages should never be documented
- [ ] How to write isolated unit tests with mocks
- [ ] The pipeline architecture and plugin system
- [ ] Pre-commit and pre-push hook requirements

**Only proceed with development tasks after ALL items are confirmed.**
# Agent Playbook

This playbook explains **how to work on GeoExhibit tasks via GitHub**. It covers the high-level workflow (issues, branches, PRs, comments) and then details how to interact with GitHub’s API using the helper scripts/templates in this repo.

---

## 1. High-Level Workflow

1. **Start from an Issue**

   * Every feature or bug is tracked as a GitHub Issue.
   * Each Issue has a goal + acceptance criteria (ACs).

2. **Create a Branch**

   * Branch names follow the pattern:

     ```
     issue-<number>-short-slug
     ```
   * Example: `issue-123-add-time-slider`.

3. **Implement**

   * Write code + tests to satisfy the Issue’s ACs.
   * Use semantic commits, e.g.:

     ```
     feat(map): add time slider (refs #123)
     ```
   * Keep commits small, one test + one unit of code each.

4. **Open a Pull Request**

   * Create a draft PR that links back to the Issue (`closes #123`).
   * The PR template has a checklist for ACs — update it.

5. **Respond to Comments**

   * Review comments are fetched via script/API.
   * Address each comment with either:

     * a code change (new commit), or
     * a written reply via PR comment.
   * Track which comments were resolved.

6. **Merge**

   * A PR is merged only when:

     * All ACs checked off,
     * CI is green,
     * Human reviewer approves.
   * After merge, delete the branch.

---

## 2. GitHub API / Script Details

The repo includes helper scripts (`/scripts/*.sh`) and a `Makefile` wrapper. These allow you to work without reading the API docs every time.

### 2.1 Issues

* **Create an issue**

  ```bash
  make issue TITLE="Add X" BODY="Goal:\nACs:\n" LABELS="agent"
  ```
* Uses: `scripts/issue_create.sh` → POST `/issues`.

### 2.2 Branches

* **Create a branch from base**

  ```bash
  make branch ISSUE=123 BRANCH="issue-123-x"
  ```
* Uses: `scripts/branch_create.sh` → GET base ref + POST `/git/refs`.

### 2.3 Pull Requests

* **Create a draft PR**

  ```bash
  make pr BRANCH="issue-123-x" TITLE="feat: X (closes #123)" BODY="Implements ACs"
  ```
* Uses: `scripts/pr_create.sh` → POST `/pulls`.

### 2.4 PR Comments

* **Fetch review comments**

  ```bash
  make comments PR=456
  ```

  → GET `/pulls/{pr}/comments` + `/pulls/{pr}/reviews`.

* **Post a reply**

  ```bash
  make comment PR=456 BODY="Resolved in abc123: fixed null check"
  ```

  → POST `/issues/{pr}/comments`.

---

## 3. Key Conventions

* **Commit discipline**: semantic messages, no WIP/noise.
* **CI gate**: never merge unless green.
* **Decision logging**: if you make a non-obvious choice, update `DECISIONS.md`.
* **Minimal inputs**: only Issue #, Branch name, and PR # are required for API calls — all other details are derived.


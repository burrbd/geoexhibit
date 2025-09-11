#!/usr/bin/env python3
"""CI Gate checker for GitHub Actions workflow status."""

import os
import json
import urllib.request
import urllib.parse
from typing import Optional, Dict, Any


def get_github_token() -> Optional[str]:
    """Get GitHub token from environment."""
    return os.environ.get('GITHUB_TOKEN')


def check_latest_workflow_run(
    owner: str, repo: str, token: Optional[str] = None
) -> Dict[str, Any]:
    """
    Check the status of the latest workflow run for the current branch.

    Returns dict with status info including:
    - success: bool
    - conclusion: str
    - html_url: str
    - logs_url: str if failed
    """
    if not token:
        token = get_github_token()

    if not token:
        return {
            "error": (
                "No GitHub token available - set GITHUB_TOKEN environment variable"
            )
        }

    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }

    try:
        # Get latest workflow runs
        base_url = f"https://api.github.com/repos/{owner}/{repo}/actions/runs"
        params = urllib.parse.urlencode({"per_page": 1, "status": "completed"})
        url = f"{base_url}?{params}"

        req = urllib.request.Request(url, headers=headers)

        with urllib.request.urlopen(req) as response:
            if response.status != 200:
                return {
                    "error": f"GitHub API returned status {response.status}"
                }

            data = json.loads(response.read().decode())

        if not data.get("workflow_runs"):
            return {"error": "No workflow runs found"}

        latest_run = data["workflow_runs"][0]

        result = {
            "success": latest_run["conclusion"] == "success",
            "conclusion": latest_run["conclusion"],
            "status": latest_run["status"],
            "html_url": latest_run["html_url"],
            "created_at": latest_run["created_at"],
            "updated_at": latest_run["updated_at"],
            "head_sha": latest_run["head_sha"]
        }

        # If failed, get logs URL
        if not result["success"]:
            result["logs_url"] = latest_run["logs_url"]

        return result

    except urllib.error.HTTPError as e:
        return {"error": f"GitHub API HTTP error {e.code}: {e.reason}"}
    except urllib.error.URLError as e:
        return {"error": f"GitHub API URL error: {e.reason}"}
    except Exception as e:
        return {"error": f"Unexpected error: {str(e)}"}


def main():
    """CLI interface for checking CI status."""
    import sys

    if len(sys.argv) != 3:
        print("Usage: python ci_gate.py <owner> <repo>")
        print("Example: python ci_gate.py myuser myrepo")
        sys.exit(1)

    owner, repo = sys.argv[1], sys.argv[2]

    result = check_latest_workflow_run(owner, repo)

    if "error" in result:
        print(f"❌ Error: {result['error']}")
        sys.exit(1)

    if result["success"]:
        print(f"✅ CI PASSED - Latest workflow run succeeded")
        print(f"   Status: {result['conclusion']}")
        print(f"   URL: {result['html_url']}")
        sys.exit(0)
    else:
        print(f"❌ CI FAILED - Latest workflow run failed")
        print(f"   Status: {result['conclusion']}")
        print(f"   URL: {result['html_url']}")
        if "logs_url" in result:
            print(f"   Logs: {result['logs_url']}")
        print("\nCI must be green before continuing development!")
        sys.exit(1)


if __name__ == "__main__":
    main()
#!/usr/bin/env bash
set -euo pipefail

: "${GH_TOKEN:?GH_TOKEN not set}"
: "${GH_REPO:?GH_REPO not set}"

api() {
  local method="$1"; shift
  local path="$1"; shift
  curl -sS -X "$method" \
    -H "Authorization: Bearer $GH_TOKEN" \
    -H "Accept: application/vnd.github+json" \
    -H "X-GitHub-Api-Version: 2022-11-28" \
    "$@" "https://api.github.com/repos/${GH_REPO}${path}"
}

# auto-detect gh cli when available for convenience
if command -v gh >/dev/null 2>&1; then
  export GH_CLI_AVAILABLE=1
else
  export GH_CLI_AVAILABLE=0
fi

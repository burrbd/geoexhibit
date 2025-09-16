#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/gh_api.sh"

BRANCH="${1:?Branch name required}"
TITLE="${2:-"Draft: ${BRANCH}"}"
BODY="${3:-"Closes #${BRANCH#issue-}"}"
BASE="${4:-${GH_BASE_BRANCH}}"

if [ "${GH_CLI_AVAILABLE}" = "1" ]; then
  gh pr create --head "$BRANCH" --base "$BASE" --title "$TITLE" --body "$BODY" --repo "$GH_REPO" --draft
else
  json=$(jq -n --arg t "$TITLE" --arg h "$BRANCH" --arg b "$BASE" --arg body "$BODY" \
    '{title:$t, head:$h, base:$b, body:$body, draft:true}')
  api POST "/pulls" -d "$json"
fi

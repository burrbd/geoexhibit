#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/gh_api.sh"

PR_NUMBER="${1:?PR number required}"
BODY="${2:?Comment body required}"

if [ "${GH_CLI_AVAILABLE}" = "1" ]; then
  gh pr comment "$PR_NUMBER" --body "$BODY" --repo "$GH_REPO"
else
  json=$(jq -n --arg body "$BODY" '{body:$body}')
  api POST "/issues/${PR_NUMBER}/comments" -d "$json"
fi

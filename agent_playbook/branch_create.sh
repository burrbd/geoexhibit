#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/gh_api.sh"

ISSUE_NUM="${1:?Issue number required}"
BRANCH_NAME="${2:-"issue-${ISSUE_NUM}"}"
BASE="${3:-${GH_BASE_BRANCH}}"

# get base sha
BASE_SHA=$(api GET "/git/ref/heads/${BASE}" | jq -r '.object.sha')

# create branch
json=$(jq -n --arg ref "refs/heads/${BRANCH_NAME}" --arg sha "$BASE_SHA" '{ref:$ref, sha:$sha}')
api POST "/git/refs" -d "$json" >/dev/null

echo "$BRANCH_NAME"

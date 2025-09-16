#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/gh_api.sh"

TITLE="${1:?Issue title required}"
BODY="${2:-"No description."}"
LABELS="${3:-"agent,auto"}"   # comma-separated or empty

if [ "${GH_CLI_AVAILABLE}" = "1" ]; then
  gh issue create --title "$TITLE" --body "$BODY" ${LABELS:+--label "$LABELS"} --repo "$GH_REPO"
else
  # Build JSON
  json=$(jq -n --arg t "$TITLE" --arg b "$BODY" --arg l "$LABELS" '
    {title:$t, body:$b} + ( ($l|length)>0 and ($l|split(",")|map(.|gsub("^ +| +$";""))) as $ls | if $ls then {labels:$ls} else {} end )
  ')
  api POST "/issues" -d "$json"
fi

#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/gh_api.sh"

PR_NUMBER="${1:?PR number required}"

# Review comments (inline)
api GET "/pulls/${PR_NUMBER}/comments" | jq -r '.[] | "- [\(.path):\(.line)] \(.user.login): \(.body)"'

echo ""
echo "---- Review States ----"
api GET "/pulls/${PR_NUMBER}/reviews" | jq -r '.[] | "\(.user.login): \(.state) - \(.body // "")"'

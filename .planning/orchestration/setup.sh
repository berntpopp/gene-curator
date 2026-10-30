#!/usr/bin/env bash
# usage: setup.sh WS BRANCH "OWNS" "ISSUES" [extra-note]
set -euo pipefail
SCR=${SCR:-$(dirname "$(readlink -f "$0")")}; MAIN=${MAIN:-$(git rev-parse --show-toplevel)}
WS=$1 BRANCH=$2 OWNS=$3 ISSUES=$4 NOTE=${5:-}
WT=$MAIN/../gc-wt/$WS; WT=$(readlink -m "$WT")
git -C "$MAIN" fetch -q origin master
git -C "$MAIN" worktree add -q "$WT" -b "$BRANCH" "${BASE:-origin/master}"
# own node_modules per worktree: make ci reinstalls it and would wipe a shared symlinked copy
(cd "$WT/frontend" && npm ci --no-audit --no-fund --loglevel=error)
(cd "$WT/backend" && uv sync --extra dev --frozen -q)
B=$SCR/$WS.brief.md
{ echo "You are implementer $WS on Gene Curator, worktree $WT, branch $BRANCH. Work only inside $WT. Ponytail full: smallest complete change."
  echo "Read AGENTS.md first."; echo; cat "$SCR/rules.md"; echo
  echo "Owned files (edit only these + new tests next to them): $OWNS"; echo
  echo "Issues, in this order (bodies below; acceptance criteria are the spec): $ISSUES"; echo
  [ -n "$NOTE" ] && { echo "Notes: $NOTE"; echo; }
  echo "When done: make check passes, push the branch, open a DRAFT PR to master, reply with the 15-line report."; echo; echo "# Issue bodies"
  for n in $ISSUES; do n=${n#\#}; [[ $n =~ ^[0-9]+$ ]] || continue; gh issue view $n -R berntpopp/gene-curator --json number,title,body -q '"## #\(.number) \(.title)\n\(.body)\n"'; done
} > "$B"
echo "$WT $(wc -c < "$B") bytes"

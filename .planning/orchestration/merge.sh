#!/usr/bin/env bash
# usage: merge.sh PR — loop: update branch to master, wait CI, merge only if CI gate passes on an up-to-date head
cd "${MAIN:-$(git rev-parse --show-toplevel)}"
N=$1; gh pr ready $N >/dev/null 2>&1
BR=$(gh pr view $N --json headRefName -q .headRefName)
for i in 1 2 3 4; do
  BEH=$(gh api repos/berntpopp/gene-curator/compare/master...$BR -q .behind_by)
  if [ "$BEH" != "0" ]; then gh api -X PUT repos/berntpopp/gene-curator/pulls/$N/update-branch -q .message || { echo "update-branch failed (conflict?)"; exit 2; }; sleep 15; fi
  sleep 20; for w in $(seq 1 30); do gh pr checks $N 2>&1 | grep -q "CI gate" && break; sleep 10; done; gh pr checks $N --watch >/dev/null 2>&1
  G=$(gh pr checks $N 2>&1 | awk -F'\t' '$1=="CI gate"{print $2}')
  echo "PR #$N try $i behind=$BEH CI gate: $G"
  if [ "$G" != "pass" ]; then gh pr checks $N 2>&1 | grep -v -P '\tpass\t'; exit 1; fi
  [ "$(gh api repos/berntpopp/gene-curator/compare/master...$BR -q .behind_by)" = "0" ] || continue
  gh pr merge $N --merge --delete-branch 2>&1 | tail -1; gh pr view $N --json state -q .state; exit 0
done; echo "gave up: master kept moving"; exit 3

#!/usr/bin/env bash
# usage: merge.sh PR — loop: update branch to master, wait CI, merge only if CI gate passes on an up-to-date head
cd "${MAIN:-$(git rev-parse --show-toplevel)}"
N=$1; gh pr ready $N >/dev/null 2>&1
BR=$(gh pr view $N --json headRefName -q .headRefName)
for i in 1 2 3 4; do
  BEH=$(gh api repos/berntpopp/gene-curator/compare/master...$BR -q .behind_by)
  if [ "$BEH" != "0" ]; then gh api -X PUT repos/berntpopp/gene-curator/pulls/$N/update-branch -q .message || { echo "update-branch failed (conflict?)"; exit 2; }; sleep 15; fi
  # judge the CI run on the exact head SHA; runs from draft pushes are skipped and never count
  H=$(gh pr view $N --json headRefOid -q .headRefOid); SEEN=0; G=
  # a draft-push run on this head may still be running and end skipped/cancelled: skip it and wait for the next run
  for w in $(seq 1 60); do
    R=$(gh run list --workflow ci.yml --branch "$BR" --json databaseId,headSha,conclusion --jq "[.[]|select(.headSha==\"$H\" and .databaseId>$SEEN and .conclusion!=\"skipped\" and .conclusion!=\"cancelled\")]|min_by(.databaseId).databaseId // empty")
    if [ -n "$R" ]; then
      gh run watch "$R" >/dev/null 2>&1; G=$(gh run view "$R" --json conclusion -q .conclusion)
      [ "$G" = skipped ] || [ "$G" = cancelled ] || break
      SEEN=$R; G=; continue
    fi
    # no real run on this head (pushed while draft): reopening fires a fresh pull_request event
    [ "$w" = 6 ] && { gh pr close $N >/dev/null; gh pr reopen $N >/dev/null; }
    sleep 10
  done
  [ -n "$G" ] || { echo "PR #$N: no CI run on head ${H:0:7}"; exit 1; }
  echo "PR #$N try $i behind=$BEH head=${H:0:7} run=$R: $G"
  if [ "$G" != "success" ]; then gh run view "$R" --json jobs --jq '.jobs[]|select(.conclusion!="success" and .conclusion!="skipped")|.name'; exit 1; fi
  [ "$(gh api repos/berntpopp/gene-curator/compare/master...$BR -q .behind_by)" = "0" ] || continue
  gh pr merge $N --merge --delete-branch 2>&1 | tail -1; gh pr view $N --json state -q .state; exit 0
done; echo "gave up: master kept moving"; exit 3

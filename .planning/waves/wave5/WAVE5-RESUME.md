# Wave5 stopped — explicit resume required

The owner requested shutdown. Only checkpoint/handover actions were authorized afterward.
Do not restart work from this document alone. Read the comprehensive
[shutdown handover](WAVE5-SHUTDOWN-HANDOVER.md) before any explicitly resumed work.

Root/origin master121592011fe387e6a83faffe8eaaae543f8ddea5 includes eight merged PRs.
G449 merged before STOP with actual review and green GitHub gates, but its required
fresh postmerge browser gate HAS NOT RUN. That is the first resume action; no J merge
before it. J450 f1549c4, I451 fb24408 and R452 remain unmerged. Their source reviews/CI
and exact tested trees are recorded in the handover. R's last wording/template/shutdown
facts delta still needs narrow actual Opus review. No v0.7.0 tag or release exists.

Actual Opus5.5 works again. GitHub PR/Actions metadata lag was observed; verify current
service status and exact PR head before any future gate or merge. Never force-push or
manufacture empty commits. Preserve root's six original dirty tracked files, untracked
planning reports, all worktrees and ignored local evidence. External backup locations,
fifteen raw-file restoration requirements and exact future commands are in the handover.

The genuine populated-v0.6.0 upgrade rehearsal passed; its
[report](evidence/upgrade-v060/REPORT.md) preserves migration/API/UI and fingerprint
provenance. It is separate from G's missing postmerge gate. Follow-ups447/448/453 and
excluded386 remain unresolved; accepted-scope epic264 is closed. No backfill or new scope.

# Deferred Enhancements

These enhancements are **deferred** because they solve problems Gene Curator doesn't currently have. They're optimized for high-throughput data aggregation (kidney-genetics-db's use case), not interactive curation workflows.

## Deferred Issues

| ID | Enhancement | Reason for Deferral |
|----|-------------|---------------------|
| 002 | CacheService L1/L2 | Write-heavy curation platform doesn't benefit from read-optimized caching (95% hit rate is for read-heavy APIs). Use simple memoization instead. |
| 005 | Real-Time Progress | Only useful for long-running batch operations (>30 min). Gene Curator has interactive workflows. Defer until confirmed need. |
| 007 | View Management | Topological sort is over-engineering for <5 views. Manually order views in SQL until complexity justifies automation. |

## When to Revisit

**002 - CacheService**: If Gene Curator becomes a public API with high read traffic (unlikely - it's a curation tool, not a data service).

**005 - Real-Time Progress**: If you implement:
- Bulk curation imports (hundreds of records)
- Scope-wide scoring recalculations
- Batch validation operations taking >5 minutes

**007 - View Management**: If you have >5 interdependent database views with complex refresh requirements.

## Estimated Savings

Deferring these issues saves **15-20 hours** of implementation time that should be invested in actual curation features instead.

---

**Note**: These are excellent implementations for their intended use case (high-throughput data pipelines). They're deferred for Gene Curator, not rejected universally.

import { defineStore } from 'pinia'
import { geneResolveAPI } from '@/api/geneResolve'
import { genesAPI } from '@/api/genes'
import { assignmentsAPI } from '@/api/assignments'
import type { Schema } from '@/types/api'

/** A resolved gene the user chose to add; `gene_id` is null while it only exists at HGNC. */
export type IntakePick = Pick<Schema<'GeneCandidate'>, 'hgnc_id' | 'symbol' | 'name' | 'gene_id'>

export interface IntakeResult {
  added: number
  alreadyInScope: number
  failed: number
  /** Added, but the curator could not be set on them. */
  notAssigned: number
}

/** The backend caps bulk create and bulk assign at 100 items per request. */
const CHUNK = 100
const LOOKUP_CONCURRENCY = 5

const chunks = <T>(items: T[]): T[][] =>
  Array.from({ length: Math.ceil(items.length / CHUNK) }, (_, i) =>
    items.slice(i * CHUNK, (i + 1) * CHUNK)
  )

export const useGeneIntakeStore = defineStore('geneIntake', () => {
  const resolve = (symbols: string[], scopeId?: string) => geneResolveAPI.resolve(symbols, scopeId)

  /** Existing gene ids for HGNC ids that were created elsewhere meanwhile (no multi-id endpoint exists). */
  async function lookup(hgncIds: string[]): Promise<string[]> {
    const ids: string[] = []
    for (let i = 0; i < hgncIds.length; i += LOOKUP_CONCURRENCY) {
      const found = await Promise.all(
        hgncIds.slice(i, i + LOOKUP_CONCURRENCY).map(async h => {
          const hit = (await genesAPI.searchGenes({ hgnc_id: h }))[0]
          return hit?.hgnc_id === h ? hit.id : undefined
        })
      )
      ids.push(...found.flatMap(id => (id ? [id] : [])))
    }
    return ids
  }

  /**
   * Create genes missing locally, then assign all of them to the scope. Both steps run in chunks
   * of 100; a failing chunk counts its genes as failed and the rest carry on. A curator, when
   * given, is set in a second call on the new assignments only: the bulk endpoint would also
   * take over unassigned genes already in the scope (curator and priority), which must keep theirs.
   * A due date goes with the first call: the API sets it on created rows only.
   */
  async function addToScope(
    scopeId: string,
    picks: IntakePick[],
    curatorId: string | null = null,
    dueDate: string | null = null
  ): Promise<IntakeResult> {
    const unique = [...new Map(picks.map(p => [p.hgnc_id, p])).values()]
    const ids = unique.flatMap(p => (p.gene_id ? [p.gene_id] : []))
    let failed = 0

    for (const chunk of chunks(unique.filter(p => !p.gene_id))) {
      try {
        const created = await genesAPI.bulkCreateGenes({
          genes: chunk.map(p => ({
            hgnc_id: p.hgnc_id,
            approved_symbol: p.symbol,
            details: p.name ? { approved_name: p.name } : undefined
          })),
          validate_hgnc: true,
          skip_duplicates: true
        })
        failed += created.total_errors
        const skipped = created.skipped_genes.map(s => s.hgnc_id as string)
        let found: string[] = []
        try {
          found = await lookup(skipped)
        } catch {
          // created genes still proceed; only the skipped ones are unresolved
        }
        failed += skipped.length - found.length
        ids.push(...created.created_genes.map(g => g.id), ...found)
      } catch {
        failed += chunk.length
      }
    }

    let added = 0
    let alreadyInScope = 0
    let notAssigned = 0
    for (const chunk of chunks(ids)) {
      try {
        const r = await assignmentsAPI.bulkAssignGenes({
          gene_ids: chunk,
          scope_id: scopeId,
          assigned_curator_id: null,
          priority_level: 'medium',
          ...(dueDate ? { due_date: dueDate } : {})
        })
        added += r.total_created
        alreadyInScope += r.total_skipped
        failed += r.total_errors
        const created = curatorId ? r.created_assignments.map(a => a.gene_id) : []
        if (created.length) {
          try {
            await assignmentsAPI.bulkAssignGenes({
              gene_ids: created,
              scope_id: scopeId,
              assigned_curator_id: curatorId,
              priority_level: 'medium'
            })
          } catch {
            notAssigned += created.length
          }
        }
      } catch {
        failed += chunk.length
      }
    }
    return { added, alreadyInScope, failed, notAssigned }
  }

  return { resolve, addToScope }
})

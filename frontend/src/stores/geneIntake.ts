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
}

export const useGeneIntakeStore = defineStore('geneIntake', () => {
  const resolve = (symbols: string[]) => geneResolveAPI.resolve(symbols)

  /** Create genes missing locally, then assign all of them to the scope in one bulk request. */
  async function addToScope(scopeId: string, picks: IntakePick[]): Promise<IntakeResult> {
    const ids = picks.flatMap(p => (p.gene_id ? [p.gene_id] : []))
    const missing = picks.filter(p => !p.gene_id)
    let failed = 0
    if (missing.length) {
      const created = await genesAPI.bulkCreateGenes({
        genes: missing.map(p => ({
          hgnc_id: p.hgnc_id,
          approved_symbol: p.symbol,
          details: p.name ? { approved_name: p.name } : undefined
        })),
        validate_hgnc: true,
        skip_duplicates: true
      })
      failed += created.total_errors
      ids.push(...created.created_genes.map(g => g.id))
      // Created by someone else in the meantime: assign the existing row
      const existing = await Promise.all(
        created.skipped_genes.map(
          async s => (await genesAPI.searchGenes({ hgnc_id: s.hgnc_id as string }))[0]
        )
      )
      ids.push(...existing.flatMap(g => (g ? [g.id] : [])))
    }
    if (!ids.length) return { added: 0, alreadyInScope: 0, failed }
    const r = await assignmentsAPI.bulkAssignGenes({
      gene_ids: ids,
      scope_id: scopeId,
      assigned_curator_id: null,
      priority_level: 'medium'
    })
    return {
      added: r.total_created,
      alreadyInScope: r.total_skipped,
      failed: failed + r.total_errors
    }
  }

  return { resolve, addToScope }
})

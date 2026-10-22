// W5 CORE fixture bootstrap (authenticated API only; fresh-stack safe; new isolated scope per run).
// Shared (idempotent by name): minimal derived schemas + workflow pair. Per run: scope w5c-<suffix>, memberships, 2 gene assignments.
//   "W5 Minimal Precuration"         derived from published "ClinGen Precuration" latest version, minimal fields
//   "W5 Minimal Curation 2-reviewer"  derived from published "ClinGen Gene-Disease Validity SOP" latest version,
//                                     minimal fields, keeps its scoring_configuration, workflow_states.review.reviewers_required=2
// Published source schemas/snapshots are never modified (derive -> edit the copy -> publish a new version of the copy).
// Memberships: admin = creator/scope admin (2nd reviewer), alice curator, bob reviewer accepted; carol viewer LEFT PENDING
// (core runner checks pending-deny in UI, then accepts in UI).
// Genes: existing PKD1/PKD2 reused; else HGNC via API; else (offline) SQL seed of a fixture gene row (documented fallback).
// Usage: node /tmp/w5-baseline-bootstrap-core.cjs   -> writes ids().core in /tmp/w5-baseline-ids.json
const { execFileSync } = require('child_process')
const { api, ids, saveIds, USERS } = require('/tmp/w5-baseline-harness.cjs')
const PRE = 'W5 Minimal Precuration'
const CUR = 'W5 Minimal Curation 2-reviewer'
const PAIR = 'W5 Minimal Workflow'
const DB = process.env.W5_DB_CONTAINER || 'gc-monkey-db'
const GENES = [['HGNC:9008', 'PKD1'], ['HGNC:9009', 'PKD2']]

// two sections: a single-section schema renders an empty tablist (useFormTabs hasTabs vs validTabs<2; see report)
const PRE_FD = { sections: [{ id: 'entity', label: 'Entity', description: 'W5 minimal precuration fixture', fields: [
  { id: 'disease_name', type: 'text', label: 'Disease Name', required: true },
  { id: 'mode_of_inheritance', type: 'select', label: 'Mode of Inheritance', required: true,
    options: [{ label: 'Autosomal Dominant', value: 'AD' }, { label: 'Autosomal Recessive', value: 'AR' }] }] },
  { id: 'details', label: 'Details', fields: [
  { id: 'entity_confirmed', type: 'boolean', label: 'Entity confirmed?', required: true, default: false },
  { id: 'curator_notes', type: 'textarea', label: 'Curator Notes', required: false }] }] }
const CUR_FD = { sections: [{ id: 'summary', label: 'Summary', description: 'W5 minimal curation fixture', fields: [
  { id: 'disease_name', type: 'text', label: 'Disease Name', required: true },
  { id: 'evidence_strength', type: 'select', label: 'Evidence Strength', required: true,
    options: [{ label: 'Limited', value: 'limited' }, { label: 'Moderate', value: 'moderate' }, { label: 'Strong', value: 'strong' }] }] },
  { id: 'assessment', label: 'Assessment', fields: [
  { id: 'evidence_summary', type: 'textarea', label: 'Evidence Summary', required: true },
  { id: 'conflict_noted', type: 'boolean', label: 'Conflicting evidence noted?', required: true, default: false },
  { id: 'curator_notes', type: 'textarea', label: 'Curator Notes', required: false }] }] }

const must = (r, what) => {
  if (r.status >= 300) throw new Error(`${what}: ${r.status} ${JSON.stringify(r.data).slice(0, 400)}`)
  return r.data
}

async function derived(all, srcName, name, fd, requiredFields, reviewers) {
  let s = all.find(x => x.name === name)
  if (!s) {
    const src = all.find(x => x.name === srcName)
    const [latest] = must(await api('admin', 'GET', `/schemas/curation-schemas/${src.id}/versions`), `${srcName} versions`)
    s = must(await api('admin', 'POST', `/schemas/curation-schemas/${src.id}/versions/${latest.id}/derive`,
      { name, version: 'w5.1' }), `derive ${name}`)
  }
  const [v] = must(await api('admin', 'GET', `/schemas/curation-schemas/${s.id}/versions`), `${name} versions`)
  const snap = v?.snapshot || {}
  const ready = JSON.stringify(snap.field_definitions) === JSON.stringify(fd) &&
    (!reviewers || snap.workflow_states?.review?.reviewers_required === reviewers)
  if (!ready) {
    const full = must(await api('admin', 'GET', `/schemas/curation-schemas/${s.id}`), `get ${name}`)
    const ws = reviewers
      ? { ...full.workflow_states, review: { ...(full.workflow_states?.review || {}), reviewers_required: reviewers } }
      : full.workflow_states
    must(await api('admin', 'PUT', `/schemas/curation-schemas/${s.id}`, {
      field_definitions: fd, validation_rules: { required_fields: requiredFields },
      ui_configuration: { form_layout: 'tabbed' }, workflow_states: ws, is_active: true
    }), `configure ${name}`)
    must(await api('admin', 'POST', `/schemas/curation-schemas/${s.id}/versions`), `publish ${name}`)
  } else if (!s.is_active) {
    must(await api('admin', 'PUT', `/schemas/curation-schemas/${s.id}`, { is_active: true }), `activate ${name}`)
  }
  return s.id
}

async function gene(hgnc, symbol) {
  const g = await api('admin', 'GET', `/genes/hgnc/${encodeURIComponent(hgnc)}`)
  if (g.status === 200 && g.data?.id) return { id: g.data.id, source: 'existing' }
  const c = await api('admin', 'POST', '/genes/', { hgnc_id: hgnc, approved_symbol: symbol })
  if (c.status < 300) return { id: c.data.id, source: 'api-hgnc' }
  // offline fallback: isolated fixture gene row (no workflow state involved)
  const out = execFileSync('docker', ['exec', DB, 'psql', '-U', process.env.W5_DB_USER || 'dev_user', '-d', 'gene_curator_dev', '-At', '-c',
    `INSERT INTO genes (hgnc_id, approved_symbol, record_hash) VALUES ('${hgnc}', '${symbol}', md5('${hgnc}')) ON CONFLICT DO NOTHING RETURNING id`]).toString().trim()
  return { id: out.split('\n')[0], source: 'sql-fallback' }
}

;(async () => {
  const t0 = Date.now()
  const all = must(await api('admin', 'GET', '/schemas/curation-schemas?active_only=false'), 'schemas')
  const preId = await derived(all, 'ClinGen Precuration', PRE, PRE_FD, ['disease_name', 'mode_of_inheritance'])
  const curId = await derived(all, 'ClinGen Gene-Disease Validity SOP', CUR, CUR_FD, ['disease_name', 'evidence_summary', 'evidence_strength'], 2)
  const pairs = must(await api('admin', 'GET', '/schemas/workflow-pairs'), 'pairs')
  const pair = pairs.find(p => p.name === PAIR) || must(await api('admin', 'POST', '/schemas/workflow-pairs', {
    name: PAIR, version: '1.0.0', description: 'W5 minimal fixture: 2 independent curation reviewers',
    precuration_schema_id: preId, curation_schema_id: curId, is_active: true }), 'pair')
  const suffix = Date.now().toString(36)
  const scope = must(await api('admin', 'POST', '/scopes/', {
    name: `w5c-${suffix}`, display_name: `W5 Core ${suffix}`, description: 'W5 core lifecycle fixture scope',
    is_public: false, default_workflow_pair_id: pair.id }), 'scope')
  const users = must(await api('admin', 'GET', '/users/'), 'users')
  const uid = Object.fromEntries(Object.entries(USERS).map(([k, e]) => [k, users.find(u => u.email === e).id]))
  const pendingDeny = {}
  for (const [who, role] of [['alice', 'curator'], ['bob', 'reviewer'], ['carol', 'viewer']]) {
    const m = must(await api('admin', 'POST', `/scopes/${scope.id}/invitations`, { user_id: uid[who], role, notes: 'W5 core' }), `invite ${who}`)
    pendingDeny[who] = (await api(who, 'GET', `/scopes/${scope.id}`)).status // API: pending grants nothing (expect 403/404)
    if (who !== 'carol') must(await api(who, 'POST', `/scopes/${scope.id}/invitations/${m.id}/accept`), `accept ${who}`)
  }
  const genes = {}
  for (const [hgnc, sym] of GENES) {
    genes[sym] = await gene(hgnc, sym)
    must(await api('admin', 'POST', '/gene-assignments/', {
      gene_id: genes[sym].id, scope_id: scope.id, assigned_curator_id: uid.alice, priority_level: 'high' }), `assign ${sym}`)
  }
  const core = { suffix, scopeId: scope.id, scopeName: scope.name, displayName: scope.display_name, workflowPairId: pair.id,
    precurationSchemaId: preId, curationSchemaId: curId, userIds: uid, pendingDeny, genes, bootstrapMs: Date.now() - t0 }
  saveIds({ core })
  console.log(JSON.stringify(core, null, 1))
})().catch(e => { console.error('BOOTSTRAP-CORE FAILED', e.message); process.exit(1) })

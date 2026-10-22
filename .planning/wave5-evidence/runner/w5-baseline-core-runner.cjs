// W5 CORE lifecycle runner. Every workflow action (save/submit/approve/request changes/resubmit/re-curation/accept)
// is a real UI click in Chromium; the API is used only for read-back verification and the fixture bootstrap.
// Usage: node /tmp/w5-baseline-core-runner.cjs <phase|all>   (needs ids().core from w5-baseline-bootstrap-core.cjs)
const { run } = require('/tmp/w5-baseline-harness.cjs')
const UI = 'http://localhost:5190'
const P = {}
const ORDER = []
const phase = (name, fn) => { P[name] = fn; ORDER.push(name) }
const clean = s => String(s).replace(/\s+/g, ' ').trim()

// click a button and capture the first non-GET API response it causes (null if none within timeout)
async function clickAndCapture(page, locator, urlPart, timeout = 15000) {
  const resp = page.waitForResponse(r => r.url().includes('/api/v1') && r.request().method() !== 'GET' &&
    (!urlPart || r.url().includes(urlPart)), { timeout }).catch(() => null)
  await locator.click()
  return resp
}
const desc = async r => (r ? `${r.request().method()} ${r.url().replace(/.*api\/v1/, '')} -> ${r.status()} ${(await r.text().catch(() => '')).slice(0, 160)}` : 'no request')
// confirm dialog if one opened (button matched by regex), returns its text
async function confirmDialog(page, re, fill) {
  const ov = page.locator('.v-overlay--active .v-card, .v-overlay--active [role=dialog]').last()
  if (!(await ov.count()) || !(await ov.isVisible().catch(() => false))) return null
  const t = clean(await ov.innerText())
  if (fill) { const ta = ov.locator('textarea').first(); if (await ta.count()) await ta.fill(fill) }
  const b = ov.getByRole('button', { name: re }).last()
  if (await b.count()) return { text: t, button: b }
  return { text: t }
}

// c1 | pending viewer carol: My work shows invite; deep link denied (UI); then Accept in UI; scope visible read-only
phase('c1-pending-viewer', async ({ as, check, shot, settle, ids, text }) => {
  const c = ids().core
  const page = await as('carol', { fresh: true })
  await settle(page, 600)
  check('c1 carol My work lists pending invite', (await text(page)).includes(c.displayName))
  await page.goto(`${UI}/scopes/${c.scopeId}`); await settle(page, 1000)
  const t = await text(page)
  check('c1 pending deep link denied (UI)', /not found or you don't have access|not authorized/i.test(t), clean(t).slice(0, 160))
  await shot(page, 'c1-carol-pending-denied')
  await page.goto(`${UI}/my-work`); await settle(page, 600)
  const r = await clickAndCapture(page, page.getByRole('listitem').filter({ hasText: c.displayName }).getByRole('button', { name: 'Accept' }), '/accept')
  check('c1 accept invitation via UI', r && r.status() < 300, await desc(r))
  await page.goto(`${UI}/scopes/${c.scopeId}`); await settle(page, 1000)
  check('c1 viewer sees scope after accept', (await text(page)).includes(c.displayName))
  await shot(page, 'c1-carol-viewer-scope')
})

// c2 | curator alice: Genes tab -> Gene actions -> Start Precuration; fill; Save draft; reload persists; Submit
phase('c2-precuration', async ({ as, check, shot, settle, vselect, ids, saveIds, api }) => {
  const c = ids().core
  const page = await as('alice')
  await page.goto(`${UI}/scopes/${c.scopeId}/genes`); await settle(page, 1000)
  await page.getByRole('row').filter({ hasText: 'PKD1' }).getByRole('button', { name: 'Gene actions' }).click()
  await page.locator('.v-overlay--active .v-list-item').filter({ hasText: 'Start Precuration' }).click()
  await settle(page, 1200)
  check('c2 precuration form opened', /precuration\/new/.test(page.url()), page.url())
  await page.getByRole('textbox', { name: 'Disease Name' }).fill('PKD1-related W5 fixture disease')
  await vselect(page, 'Mode of Inheritance', 'Autosomal Dominant')
  await page.getByRole('tab', { name: 'Details' }).click()
  await page.getByRole('textbox', { name: 'Curator Notes' }).fill('precuration note v1')
  await shot(page, 'c2-alice-precuration-filled')
  const r = await clickAndCapture(page, page.getByRole('button', { name: /Save Draft/ }), '/precurations')
  const body = r ? await r.json().catch(() => ({})) : {}
  check('c2 Save draft click (new) -> POST 201', r && r.status() === 201, await desc(r))
  saveIds({ core: { ...c, precurationId: body.id } })
  await settle(page, 1200)
  await page.reload(); await settle(page, 1500)
  check('c2 reload: disease name persisted', (await page.getByRole('textbox', { name: 'Disease Name' }).inputValue()) === 'PKD1-related W5 fixture disease')
  await page.getByRole('tab', { name: 'Details' }).click()
  check('c2 reload: notes persisted', (await page.getByRole('textbox', { name: 'Curator Notes' }).inputValue()) === 'precuration note v1')
  await shot(page, 'c2-alice-precuration-reloaded')
  const submit = page.getByRole('button', { name: /Submit for Review/ })
  check('c2 submit enabled with untouched required boolean (false is an answer)', await submit.isEnabled())
  const s = await clickAndCapture(page, submit, '/precurations')
  let sub = s
  if (!sub) {
    const d = await confirmDialog(page, /submit|confirm/i)
    check('c2 submit confirm dialog', !!d, d?.text)
    if (d?.button) sub = await clickAndCapture(page, d.button, '/precurations')
  }
  check('c2 submit precuration via UI', sub && sub.status() < 300, await desc(sub))
  await settle(page, 1000)
  await shot(page, 'c2-alice-precuration-submitted')
  const st = (await api('alice', 'GET', `/precurations/${body.id}`)).data
  check('c2 read-back: precuration submitted', ['submitted', 'in_review'].includes(st.status), `${st.status}/${st.workflow_stage}`)
})

// Review Queue action (UI): find the item card for gene+stage text, click Approve / Request changes, fill dialog
async function queueAction(page, { gene, stage, action, notes, shotName, shot, check, settle }) {
  await page.goto(`${UI}/review-queue?q=${gene}`); await settle(page, 1200)
  const card = page.locator('.v-card, [role=listitem], .v-list-item').filter({ hasText: gene }).filter({ hasText: stage })
    .filter({ has: page.getByRole('button', { name: action }) }).last()
  const visible = await card.count()
  if (!visible) return { ok: false, detail: `no "${action}" for ${gene}/${stage}: ${clean(await page.locator('main').innerText()).slice(0, 300)}` }
  let resp = await clickAndCapture(page, card.getByRole('button', { name: action }), null, 2500)
  let dialogText = null
  if (!resp) {
    const d = await confirmDialog(page, new RegExp(`${action}|confirm|submit`, 'i'), notes)
    dialogText = d?.text
    if (shotName) await shot(page, `${shotName}-dialog`)
    if (d?.button) resp = await clickAndCapture(page, d.button, null)
  }
  await settle(page, 1000)
  if (shotName) await shot(page, shotName)
  const snack = clean((await page.locator('.v-snackbar').allInnerTexts()).join(' | '))
  return { ok: !!resp && resp.status() < 300, detail: `${await desc(resp)} dialog=[${(dialogText || '').slice(0, 160)}] snack=[${snack.slice(0, 160)}]`, status: resp?.status() }
}

// c3 | reviewer bob: Review Queue -> Approve precuration (D1: author alice has no review role); curation auto-created
phase('c3-precuration-approve', async ({ as, check, shot, settle, ids, saveIds, api }) => {
  const c = ids().core
  const page = await as('bob')
  const r = await queueAction(page, { gene: 'PKD1', stage: 'Precuration', action: 'Approve', notes: 'W5 precuration approved by bob', shotName: 'c3-bob-precuration-approve', shot, check, settle })
  check('c3 bob approves precuration via Review Queue', r.ok, r.detail)
  const pre = (await api('bob', 'GET', `/precurations/${c.precurationId}`)).data
  check('c3 read-back: precuration approved', pre.status === 'approved', `${pre.status}/${pre.workflow_stage}`)
  const list = (await api('alice', 'GET', `/curations/?scope_id=${c.scopeId}`)).data
  const cur = (list.curations || list.items || list).find?.(x => x.gene_id === c.genes.PKD1.id)
  check('c3 read-back: curation auto-created for author alice', cur && cur.created_by === c.userIds.alice, cur ? `${cur.id} ${cur.status} created_by=${cur.created_by}` : JSON.stringify(list).slice(0, 200))
  if (cur) saveIds({ core: { ...c, curationId: cur.id } })
})

// submit from the curation edit page (UI), handling an optional confirm dialog
async function submitCuration(page, curationId) {
  const btn = page.getByRole('button', { name: /Submit for review/i }).first()
  const enabled = await btn.isEnabled()
  let resp = await clickAndCapture(page, btn, `/curations/${curationId}/submit`, 4000)
  let dialog = null
  if (!resp) {
    const d = await confirmDialog(page, /submit|confirm|resubmit/i)
    dialog = d?.text
    if (d?.button) resp = await clickAndCapture(page, d.button, `/curations/${curationId}/submit`)
  }
  return { enabled, resp, dialog }
}

// c4 | curator alice: curation edit -> fill -> Save draft click -> reload persists -> unsaved-restore probe -> Submit (round 1)
phase('c4-curation-draft-submit', async ({ as, check, shot, settle, vselect, ids, api }) => {
  const c = ids().core
  const page = await as('alice')
  const edit = `${UI}/scopes/${c.scopeId}/curations/${c.curationId}/edit`
  await page.goto(edit); await settle(page, 1500)
  await page.getByRole('textbox', { name: 'Disease Name' }).fill('PKD1-related W5 fixture disease')
  await vselect(page, 'Evidence Strength', 'Moderate')
  await page.getByRole('tab', { name: 'Assessment' }).click()
  await page.getByRole('textbox', { name: 'Evidence Summary' }).fill('Round 1 evidence summary (fixture text, not clinical).')
  await page.getByRole('textbox', { name: 'Curator Notes' }).fill('curation note v1')
  await shot(page, 'c4-alice-curation-filled')
  const r = await clickAndCapture(page, page.getByRole('button', { name: 'Save draft' }), `/curations/${c.curationId}`)
  check('c4 Save draft click (immediately after typing) saves', r && r.status() < 300, await desc(r))
  await settle(page, 1000)
  await page.reload(); await settle(page, 1500)
  check('c4 reload: disease name persisted', (await page.getByRole('textbox', { name: 'Disease Name' }).inputValue()) === 'PKD1-related W5 fixture disease')
  const es = clean(await page.locator('.v-input').filter({ has: page.getByRole('combobox', { name: 'Evidence Strength' }) }).innerText())
  check('c4 reload: evidence strength persisted', /Moderate/.test(es), es)
  await page.getByRole('tab', { name: 'Assessment' }).click()
  check('c4 reload: evidence summary persisted', (await page.getByRole('textbox', { name: 'Evidence Summary' }).inputValue()).startsWith('Round 1'))
  await shot(page, 'c4-alice-curation-reloaded')
  // Wave4 probe: unsaved local edit + reload -> restore prompt? does restoring overwrite newer server state?
  await page.getByRole('textbox', { name: 'Curator Notes' }).fill('UNSAVED local edit')
  await page.waitForTimeout(2500)
  await page.reload(); await settle(page, 1500)
  const ov = page.locator('.v-overlay--active').filter({ hasText: /Restore unsaved changes/i })
  const restoreShown = await ov.isVisible().catch(() => false)
  check('c4 probe: restore-unsaved prompt after reload', restoreShown, restoreShown ? clean(await ov.innerText()).slice(0, 200) : 'no prompt')
  await shot(page, 'c4-alice-unsaved-reload-probe')
  if (restoreShown) {
    await ov.getByRole('button', { name: 'Restore' }).click(); await settle(page, 600)
    await page.getByRole('tab', { name: 'Assessment' }).click()
    const n = await page.getByRole('textbox', { name: 'Curator Notes' }).inputValue()
    check('c4 probe: Restore replaces whole form with local buffer (info)', n === 'UNSAVED local edit', `notes="${n}"`)
  }
  await page.getByRole('tab', { name: 'Assessment' }).click()
  await page.getByRole('textbox', { name: 'Curator Notes' }).fill('curation note v1')
  const { enabled, resp, dialog } = await submitCuration(page, c.curationId)
  check('c4 submit enabled when valid', enabled)
  check('c4 submit round 1 via UI', resp && resp.status() < 300, `${await desc(resp)} dialog=[${(dialog || '').slice(0, 160)}]`)
  await settle(page, 1200)
  await shot(page, 'c4-alice-curation-submitted')
  const cur = (await api('alice', 'GET', `/curations/${c.curationId}`)).data
  check('c4 read-back: in review', cur.status === 'in_review' || cur.workflow_stage === 'review', `${cur.status}/${cur.workflow_stage} notes=${cur.evidence_data?.curator_notes}`)
})

// curation review action on the curation detail page (UI): Approve / Request changes + dialog notes
async function detailAction(page, c, { action, notes, shotName, shot, settle }) {
  await page.goto(`${UI}/scopes/${c.scopeId}/curations/${c.curationId}`); await settle(page, 1500)
  const btn = page.getByRole('main').getByRole('button', { name: action, exact: true })
  if (!(await btn.count())) return { ok: false, detail: `no "${action}" button: ${clean(await page.locator('main').innerText()).slice(0, 300)}` }
  if (!(await btn.first().isEnabled())) return { ok: false, detail: `"${action}" disabled` }
  let accepted = 0
  if (action === 'Approve') {
    // reviewer must Accept (or resolve) every changed evidence item first
    const region = page.getByRole('region', { name: 'Evidence changes' })
    for (let i = 0; i < 30; i++) {
      const open = region.locator('button[aria-pressed="false"]').filter({ hasText: /^\s*Accept\s*$/ })
      if (!(await open.count())) break
      await open.first().click(); accepted++
      await page.waitForTimeout(500)
    }
  }
  let resp = await clickAndCapture(page, btn.first(), c.curationId, 2500)
  let dialog = null
  if (!resp) {
    const boxes = page.locator('.v-overlay--active').last().getByRole('checkbox')
    for (let i = 0; i < await boxes.count(); i++) await boxes.nth(i).check()
    const d = await confirmDialog(page, new RegExp(`^(${action}|confirm|submit|send)`, 'i'), notes)
    dialog = d?.text
    if (shotName) await shot(page, `${shotName}-dialog`)
    if (d?.button) resp = await clickAndCapture(page, d.button, c.curationId)
  }
  await settle(page, 1000)
  if (shotName) await shot(page, shotName)
  const snack = clean((await page.locator('.v-snackbar').allInnerTexts()).join(' | '))
  return { ok: !!resp && resp.status() < 300, detail: `accepted=${accepted} ${await desc(resp)} dialog=[${(dialog || '').slice(0, 200)}] snack=[${snack.slice(0, 160)}]` }
}

const curState = async (api, c) => (await api('admin', 'GET', `/curations/${c.curationId}`)).data

// c5 | reviewer bob: round 1 Request changes via Review Queue
phase('c5-round1-request-changes', async ({ as, check, shot, settle, ids, api }) => {
  const c = ids().core
  const page = await as('bob')
  const r = await detailAction(page, c, { action: 'Request changes', notes: 'Round 1: please expand the evidence summary.', shotName: 'c5-bob-request-changes', shot, settle })
  check('c5 bob requests changes (round 1) via UI', r.ok, r.detail)
  const cur = await curState(api, c)
  check('c5 read-back: back to curation draft', cur.workflow_stage === 'curation', `${cur.status}/${cur.workflow_stage}`)
})

// c6 | curator alice: sees changes requested, edits, Save draft, reload, resubmit (round 2)
phase('c6-resubmit', async ({ as, check, shot, settle, ids, api, text }) => {
  const c = ids().core
  const page = await as('alice')
  await page.goto(`${UI}/my-work`); await settle(page, 1000)
  const mw = clean(await text(page))
  check('c6 My work surfaces the changes request', /PKD1/.test(mw), (mw.match(/.{0,80}PKD1.{0,120}/) || [''])[0])
  await shot(page, 'c6-alice-mywork-changes-requested')
  await page.goto(`${UI}/scopes/${c.scopeId}/curations/${c.curationId}/edit`); await settle(page, 1500)
  const ov = page.locator('.v-overlay--active').filter({ hasText: /Restore unsaved changes/i })
  if (await ov.isVisible().catch(() => false)) { await ov.getByRole('button', { name: 'Discard' }).click(); await settle(page, 500) }
  const body = clean(await text(page))
  check('c6 edit page shows reviewer feedback (info)', /expand the evidence summary|changes requested|request/i.test(body), (body.match(/.{0,60}(expand the evidence|changes requested).{0,60}/i) || ['not shown on edit page'])[0])
  await page.getByRole('tab', { name: 'Assessment' }).click()
  await page.getByRole('textbox', { name: 'Evidence Summary' }).fill('Round 2 evidence summary, expanded per reviewer request (fixture text).')
  const r = await clickAndCapture(page, page.getByRole('button', { name: 'Save draft' }), `/curations/${c.curationId}`)
  check('c6 Save draft after changes requested', r && r.status() < 300, await desc(r))
  await settle(page, 800); await page.reload(); await settle(page, 1500)
  const ov2 = page.locator('.v-overlay--active').filter({ hasText: /Restore unsaved changes/i })
  check('c6 no restore prompt after a clean save+reload', !(await ov2.isVisible().catch(() => false)))
  if (await ov2.isVisible().catch(() => false)) { await ov2.getByRole('button', { name: 'Discard' }).click(); await settle(page, 500) }
  await page.getByRole('tab', { name: 'Assessment' }).click()
  check('c6 reload: round 2 summary persisted', (await page.getByRole('textbox', { name: 'Evidence Summary' }).inputValue()).startsWith('Round 2'))
  const { resp, dialog } = await submitCuration(page, c.curationId)
  check('c6 resubmit (round 2) via UI', resp && resp.status() < 300, `${await desc(resp)} dialog=[${(dialog || '').slice(0, 120)}]`)
  await settle(page, 1000); await shot(page, 'c6-alice-resubmitted')
  const cur = await curState(api, c)
  check('c6 read-back: in review again', cur.status === 'in_review', `${cur.status}/${cur.workflow_stage}`)
})

// c7 | reviewer bob: round 2 Approve -> stays in review (1 of 2); repeat approve not offered
phase('c7-round2-first-approve', async ({ as, check, shot, settle, ids, api }) => {
  const c = ids().core
  const page = await as('bob')
  const r = await detailAction(page, c, { action: 'Approve', notes: 'Round 2 approve #1 (bob)', shotName: 'c7-bob-approve', shot, settle })
  check('c7 bob approves round 2 via UI', r.ok, r.detail)
  const cur = await curState(api, c)
  check('c7 read-back: still in review after 1 of 2 approvals', cur.status === 'in_review', `${cur.status}/${cur.workflow_stage}`)
  await page.goto(`${UI}/scopes/${c.scopeId}/curations/${c.curationId}`); await settle(page, 1500)
  const btn = page.getByRole('main').getByRole('button', { name: 'Approve', exact: true })
  const n = await btn.count(), en = n ? await btn.first().isEnabled() : false
  const wa = clean(await page.locator('main').innerText()).match(/Workflow actions.{0,240}/)?.[0]
  check('c7 repeat approver: bob cannot approve again (button absent/disabled)', !n || !en, `approveButtons=${n} enabled=${en} :: ${wa}`)
  await page.goto(`${UI}/review-queue?q=PKD1`); await settle(page, 1200)
  check('c7 repeat approver: queue state for bob (info)', true, clean(await page.locator('main').innerText()).slice(120, 400))
  await shot(page, 'c7-bob-queue-after-approve')
})

// c8 | scope admin (second independent reviewer, not author): Approve -> active
phase('c8-round2-second-approve', async ({ as, check, shot, settle, ids, api }) => {
  const c = ids().core
  const page = await as('admin')
  const r = await detailAction(page, c, { action: 'Approve', notes: 'Round 2 approve #2 (scope admin)', shotName: 'c8-admin-approve', shot, settle })
  check('c8 scope admin approves (2nd independent reviewer) via UI', r.ok, r.detail)
  const cur = await curState(api, c)
  check('c8 read-back: active after 2 approvals', cur.status === 'active' || cur.workflow_stage === 'active', `${cur.status}/${cur.workflow_stage}`)
})


phase('c9-recuration-viewer', async ({ as, check, shot, settle, ids, saveIds, api }) => {
  const c = ids().core
  const viewer = await as('carol')
  await viewer.goto(`${UI}/scopes/${c.scopeId}/curations/${c.curationId}`); await settle(viewer)
  check('c9 viewer sees active curation', (await viewer.locator('main').innerText()).includes('PKD1'))
  check('c9 viewer has no write/review controls', await viewer.getByRole('main').getByRole('button', {name:/^(Edit|Save draft|Start re-curation|Approve|Request changes)$/}).count() === 0)
  await shot(viewer, 'c9-viewer-active-readonly')
  const page = await as('alice')
  await page.goto(`${UI}/scopes/${c.scopeId}/curations/${c.curationId}`); await settle(page)
  await page.getByRole('button', {name:'Start re-curation', exact:true}).click(); await settle(page)
  check('c9 re-curation has source query', page.url().includes(`from=${c.curationId}`), page.url())
  check('c9 disease prefilled', await page.getByRole('textbox', {name:'Disease Name'}).inputValue() === 'PKD1-related W5 fixture disease')
  await page.getByRole('tab',{name:'Assessment'}).click()
  check('c9 evidence summary prefilled', (await page.getByRole('textbox',{name:'Evidence Summary'}).inputValue()).startsWith('Round 2'))
  await page.getByRole('textbox',{name:'Evidence Summary'}).fill('Re-curation revised evidence summary (fixture text).')
  const r=await clickAndCapture(page,page.getByRole('button',{name:'Save draft'}),'/curations')
  check('c9 new re-curation saved via UI',r && r.status()===201,await desc(r))
  const cur=r ? await r.json():{}
  check('c9 new ID and approved precuration preserved',cur.id !== c.curationId && cur.precuration_id===c.precurationId,`${cur.id}/${cur.precuration_id}`)
  const old=await curState(api,c)
  check('c9 original remains active while new draft exists',old.status==='active',old.status)
  saveIds({core:{...c,originalCurationId:c.curationId,curationId:cur.id}})
  await settle(page);await page.reload();await settle(page)
  await page.getByRole('tab',{name:'Assessment'}).click()
  check('c9 re-curation reload retains revised data',(await page.getByRole('textbox',{name:'Evidence Summary'}).inputValue()).startsWith('Re-curation revised'))
  const {resp}=await submitCuration(page,cur.id)
  check('c9 re-curation submit via UI',resp&&resp.status()<300,await desc(resp))
  await shot(page,'c9-recuration-submitted')
})
phase('c10-recuration-activate', async ({as,check,shot,settle,ids,api})=>{
  const c=ids().core
  for(const role of ['bob','admin']){
    const page=await as(role)
    const r=await detailAction(page,c,{action:'Approve',notes:`Re-curation approved by ${role}`,shotName:`c10-${role}-recuration-approve`,shot,settle})
    check(`c10 ${role} approves re-curation via UI`,r.ok,r.detail)
  }
  const current=await curState(api,c)
  const old=(await api('admin','GET',`/curations/${c.originalCurationId}`)).data
  check('c10 replacement active and original superseded',current.status==='active' && old.status!=='active',`${current.status}/${old.status}`)
})
phase('c11-admin-d1',async({as,check,shot,settle,vselect,ids,api})=>{
  const c=ids().core
  const page=await as('admin')
  await page.goto(`${UI}/scopes/${c.scopeId}/genes/${c.genes.PKD2.id}/precuration/new`);await settle(page)
  await page.getByRole('textbox',{name:'Disease Name'}).fill('PKD2 admin authored fixture')
  await vselect(page,'Mode of Inheritance','Autosomal Dominant')
  const preSave=await clickAndCapture(page,page.getByRole('button',{name:/Save Draft/i}),'/precurations')
  check('c11 admin saves own precuration via UI',preSave&&preSave.status()===201,await desc(preSave))
  await settle(page)
  const preSubmit=await clickAndCapture(page,page.getByRole('button',{name:/Submit for Review/i}),'/precurations')
  check('c11 admin submits own precuration via UI',preSubmit&&preSubmit.status()<300,await desc(preSubmit))
  const bob=await as('bob')
  const preApprove=await queueAction(bob,{gene:'PKD2',stage:'Precuration',action:'Approve',notes:'Independent review of administrator work',shotName:'c11-bob-admin-precuration',shot,check,settle})
  check('c11 Bob independently approves admin precuration',preApprove.ok,preApprove.detail)
  const list=(await api('admin','GET',`/curations/?scope_id=${c.scopeId}`)).data
  const created=(list.curations||list.items||list).find(x=>x.gene_id===c.genes.PKD2.id)
  check('c11 curation author is platform admin',created?.created_by===c.userIds.admin,created?.created_by)
  await page.goto(`${UI}/scopes/${c.scopeId}/curations/${created.id}/edit`);await settle(page)
  await page.getByRole('textbox',{name:'Disease Name'}).fill('PKD2 admin authored fixture')
  await vselect(page,'Evidence Strength','Limited')
  await page.getByRole('tab',{name:'Assessment'}).click()
  await page.getByRole('textbox',{name:'Evidence Summary'}).fill('Administrator authored evidence; independent review required.')
  const r=await clickAndCapture(page,page.getByRole('button',{name:'Save draft'}),'/curations')
  check('c11 admin saves own draft through UI',r&&r.status()===200,await desc(r))
  const cur=r?await r.json():{}
  await settle(page)
  const {resp}=await submitCuration(page,cur.id)
  check('c11 admin submits own curation through UI',resp&&resp.status()<300,await desc(resp))
  await page.goto(`${UI}/scopes/${c.scopeId}/curations/${cur.id}`);await settle(page)
  check('c11 administrator cannot approve own work in UI',await page.getByRole('main').getByRole('button',{name:'Approve',exact:true}).count()===0)
  check('c11 own curation remains review',(await api('admin','GET',`/curations/${cur.id}`)).data.status==='in_review')
  await shot(page,'c11-admin-own-work-d1')
})

module.exports = { P, ORDER, queueAction, detailAction, submitCuration, clickAndCapture, desc }
if (require.main === module) {
  const want = process.argv[2]
  const list = want === 'all' ? ORDER : [want]
  ;(async () => { for (const name of list) await new Promise(res => run(name, P[name]).then(res)) })()
}

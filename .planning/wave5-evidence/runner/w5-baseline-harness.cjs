// W5 baseline browser harness: real Chromium via installed Playwright; every step file requires this.
// Run a step: node /tmp/w5-baseline-step-NN-*.cjs   (sessions persist in /tmp/w5-baseline-state-*.json)
const pw = require('/home/bernt-popp/development/gc-wt/monkey/frontend/node_modules/playwright')
const fs = require('fs')

const UI = 'http://localhost:5190'
const API = 'http://localhost:8052/api/v1'
const SHOTS = '/tmp/w5-baseline-shots'
const IDS = '/tmp/w5-baseline-ids.json'
const EVENTS = '/tmp/w5-baseline-events.log'
const USERS = {
  admin: 'admin@genecurator.org',
  alice: 'alice.smith@genecurator.org',
  bob: 'bob.jones@genecurator.org',
  carol: 'carol.williams@genecurator.org'
}
const PASSWORD = process.env.W5_TEST_PASSWORD
if (!PASSWORD) throw new Error('Set W5_TEST_PASSWORD to the isolated-stack seeded test password')
// font 403s come from the symlinked node_modules outside Vite's fs.allow (harness, not product)
const NOISE = /fontsource|ibm-plex|favicon/

const ids = () => (fs.existsSync(IDS) ? JSON.parse(fs.readFileSync(IDS, 'utf8')) : {})
const saveIds = patch => fs.writeFileSync(IDS, JSON.stringify({ ...ids(), ...patch }, null, 2))
const log = (step, line) => fs.appendFileSync(EVENTS, `[${new Date().toISOString()}] ${step} ${line}\n`)

async function run(stepName, body) {
  const browser = await pw.chromium.launch()
  const pages = []
  const result = { step: stepName, checks: [], errors: [] }
  const check = (name, ok, detail = '') => {
    result.checks.push({ name, ok: !!ok, detail: String(detail).slice(0, 400) })
    log(stepName, `${ok ? 'PASS' : 'FAIL'} ${name} ${String(detail).slice(0, 200)}`)
  }
  async function as(role, { fresh = false } = {}) {
    const state = `/tmp/w5-baseline-state-${role}.json`
    const ctx = await browser.newContext({
      viewport: { width: 1440, height: 900 },
      storageState: !fresh && fs.existsSync(state) ? state : undefined
    })
    const page = await ctx.newPage()
    page.on('console', m => {
      if (['error', 'warning'].includes(m.type()) && !NOISE.test(m.text() + (m.location()?.url || ''))) {
        result.errors.push(`${role} console.${m.type()} @${page.url()}: ${m.text().slice(0, 300)}`)
      }
    })
    page.on('pageerror', e => result.errors.push(`${role} pageerror @${page.url()}: ${e.message.slice(0, 300)}`))
    page.on('response', r => {
      if (r.status() >= 400 && !NOISE.test(r.url())) {
        result.errors.push(`${role} HTTP ${r.status()} ${r.request().method()} ${r.url().replace(UI, '').replace(API, '/api')}`)
      }
    })
    page.on('requestfailed', r => {
      if (!NOISE.test(r.url())) result.errors.push(`${role} requestfailed ${r.url()} ${r.failure()?.errorText}`)
    })
    pages.push(page)
    await page.goto(`${UI}/my-work`)
    await page.waitForLoadState('networkidle')
    if (page.url().includes('/login')) await uiLogin(page, role)
    await ctx.storageState({ path: state })
    return page
  }
  async function uiLogin(page, role) {
    const accept = page.getByRole('button', { name: /Accept disclaimer/ })
    if (await accept.isVisible().catch(() => false)) await accept.click()
    await page.getByRole('textbox', { name: 'Email' }).fill(USERS[role])
    await page.getByRole('textbox', { name: 'Password' }).fill(PASSWORD)
    await page.getByRole('button', { name: 'Sign in', exact: true }).click()
    await page.waitForURL(u => !u.pathname.startsWith('/login'), { timeout: 15000 })
    await page.waitForLoadState('networkidle')
  }
  try {
    await body({ as, check, shot, aria, text, settle, api, ids, saveIds, vselect, UI, API })
  } catch (e) {
    result.fatal = e.message.split('\n').slice(0, 6).join(' | ')
    log(stepName, `FATAL ${result.fatal}`)
    for (const [i, p] of pages.entries()) await shot(p, `${stepName}-FATAL-${i}`).catch(() => {})
  } finally {
    await browser.close()
  }
  for (const e of result.errors) log(stepName, `ERR ${e}`)
  console.log(JSON.stringify(result, null, 1))
  return result
}

async function shot(page, name) {
  const path = `${SHOTS}/${name}.png`
  await page.screenshot({ path, fullPage: true })
  return path
}
// Vuetify v-select/v-autocomplete: the role=combobox input is not clickable; open via its .v-field
async function vselect(page, label, option, scope = page) {
  const input = scope.locator('.v-input').filter({ has: page.getByRole('combobox', { name: label, exact: true }) }).first()
  await input.locator('.v-field').click()
  // anchored: plain substring would match "Viewer" inside "Reviewer"
  const re = option instanceof RegExp ? option : new RegExp('^\\s*' + option.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'i')
  const item = page.locator('.v-overlay--active .v-list-item').filter({ hasText: re }).first()
  await item.waitFor({ state: 'visible', timeout: 10000 })
  await item.click()
  await page.keyboard.press('Escape').catch(() => {})
}
const aria = (page, sel = 'main') => page.locator(sel).first().ariaSnapshot()
const text = async (page, sel = 'main') => (await page.locator(sel).first().innerText()).replace(/\n{2,}/g, '\n')
async function settle(page, ms = 400) {
  await page.waitForLoadState('networkidle').catch(() => {})
  await page.waitForTimeout(ms)
}
// Authenticated API call for fixture setup / read-only verification (never workflow transitions)
async function api(role, method, path, body) {
  const tok = await fetch(`${API}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email: USERS[role], password: PASSWORD })
  }).then(r => r.json())
  const r = await fetch(`${API}${path}`, {
    method,
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${tok.access_token}` },
    body: body ? JSON.stringify(body) : undefined
  })
  const t = await r.text()
  let data
  try { data = JSON.parse(t) } catch { data = t }
  return { status: r.status, data }
}

module.exports = { run, api, ids, saveIds, USERS, UI, API }

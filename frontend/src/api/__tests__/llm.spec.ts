import { describe, it, expect, vi } from 'vitest'
import apiClient from '../client'
import { llmAPI } from '../llm'

vi.mock('../client', () => ({
  default: Object.fromEntries(
    ['get', 'post', 'put', 'patch'].map(m => [m, vi.fn().mockResolvedValue({ data: 'payload' })])
  )
}))

const client = vi.mocked(apiClient)
const B = { body: 1 } as never
const A = '/admin/llm'

const rows: [string, () => Promise<unknown>, 'get' | 'post' | 'put' | 'patch', unknown[]][] = [
  ['listProviders', () => llmAPI.listProviders(), 'get', [`${A}/providers`]],
  ['createProvider', () => llmAPI.createProvider(B), 'post', [`${A}/providers`, B]],
  ['updateProvider', () => llmAPI.updateProvider('p', B), 'patch', [`${A}/providers/p`, B]],
  ['setKey', () => llmAPI.setKey('p', B), 'put', [`${A}/providers/p/key`, B]],
  ['ping', () => llmAPI.ping('p'), 'post', [`${A}/providers/p/ping`, {}]],
  ['listModels', () => llmAPI.listModels(), 'get', [`${A}/models`]],
  ['createModel', () => llmAPI.createModel(B), 'post', [`${A}/models`, B]],
  ['updateModel', () => llmAPI.updateModel('m', B), 'patch', [`${A}/models/m`, B]],
  ['usage', () => llmAPI.usage(), 'get', [`${A}/usage`]],
  ['listRuns', () => llmAPI.listRuns({ limit: 5 }), 'get', [`${A}/runs`, { params: { limit: 5 } }]],
  ['listTemplates', () => llmAPI.listTemplates(), 'get', [`${A}/prompt-templates`]],
  ['createTemplate', () => llmAPI.createTemplate(B), 'post', [`${A}/prompt-templates`, B]],
  ['listVersions', () => llmAPI.listVersions('t'), 'get', [`${A}/prompt-templates/t/versions`]],
  [
    'createVersion',
    () => llmAPI.createVersion('t', B),
    'post',
    [`${A}/prompt-templates/t/versions`, B]
  ],
  ['updateVersion', () => llmAPI.updateVersion('v', B), 'patch', [`${A}/prompt-versions/v`, B]],
  [
    'publishVersion',
    () => llmAPI.publishVersion('v', B),
    'post',
    [`${A}/prompt-versions/v/publish`, B]
  ],
  [
    'diffVersions',
    () => llmAPI.diffVersions('v', 'w'),
    'get',
    [`${A}/prompt-versions/v/diff`, { params: { against: 'w' } }]
  ],
  ['testRun', () => llmAPI.testRun('v', B), 'post', [`${A}/prompt-versions/v/test-run`, B]],
  ['scopeOptions', () => llmAPI.scopeOptions('s'), 'get', ['/scopes/s/llm-options']],
  ['scopeSettings', () => llmAPI.scopeSettings('s'), 'get', ['/scopes/s/llm-settings']],
  [
    'saveScopeSettings',
    () => llmAPI.saveScopeSettings('s', B),
    'put',
    ['/scopes/s/llm-settings', B]
  ],
  [
    'secondView',
    () => llmAPI.secondView('s', 'c'),
    'get',
    ['/scopes/s/curations/c/llm-second-view']
  ],
  [
    'requestSecondView',
    () => llmAPI.requestSecondView('s', 'c'),
    'post',
    ['/scopes/s/curations/c/llm-second-view']
  ],
  ['decideFinding', () => llmAPI.decideFinding('f', B), 'patch', ['/llm-findings/f', B]]
]

describe('llmAPI', () => {
  it.each(rows)('%s calls the right endpoint', async (_name, run, method, args) => {
    vi.clearAllMocks()
    const result = await run()
    expect(client[method]).toHaveBeenCalledWith(...args)
    if (method !== 'put' || args[0] !== `${A}/providers/p/key`) expect(result).toBe('payload')
    else expect(result).toBeUndefined() // the key endpoint returns nothing
  })
})

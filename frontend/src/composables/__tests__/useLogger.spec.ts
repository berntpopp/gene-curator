import { describe, it, expect, vi, beforeEach } from 'vitest'

vi.mock('@/services/logService', () => ({
  logService: {
    debug: vi.fn(),
    info: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
    critical: vi.fn(),
    logPerformance: vi.fn()
  }
}))

import { useLogger, getLogger } from '../useLogger'
import { logService } from '@/services/logService'

describe('useLogger', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('tags every level with the component name (Unknown outside a component)', () => {
    const logger = useLogger()

    logger.debug('d', { a: 1 })
    logger.info('i')
    logger.warn('w')
    logger.error('e', { code: 500 })
    logger.critical('c')

    expect(logService.debug).toHaveBeenCalledWith('d', { a: 1, component: 'Unknown' })
    expect(logService.info).toHaveBeenCalledWith('i', { component: 'Unknown' })
    expect(logService.warn).toHaveBeenCalledWith('w', { component: 'Unknown' })
    expect(logService.error).toHaveBeenCalledWith('e', { code: 500, component: 'Unknown' })
    expect(logService.critical).toHaveBeenCalledWith('c', { component: 'Unknown' })
  })

  it('uses an explicit component name when given', () => {
    const logger = useLogger('ScopeList')

    logger.info('loaded', { count: 2 })

    expect(logService.info).toHaveBeenCalledWith('loaded', { count: 2, component: 'ScopeList' })
  })

  it('forwards performance logging with component context', () => {
    const logger = useLogger('GeneTable')

    logger.logPerformance('dataLoad', 100, { rows: 10 })

    expect(logService.logPerformance).toHaveBeenCalledWith('dataLoad', 100, {
      rows: 10,
      component: 'GeneTable'
    })
  })

  it('getLogger derives the name from an options-API instance', () => {
    const logger = getLogger({ $options: { name: 'LegacyCard' } })

    logger.warn('legacy')

    expect(logService.warn).toHaveBeenCalledWith('legacy', { component: 'LegacyCard' })
  })

  it('getLogger falls back to type name, then Unknown', () => {
    getLogger({ type: { name: 'TypeNamed' } }).info('x')
    getLogger({}).info('y')

    expect(logService.info).toHaveBeenNthCalledWith(1, 'x', { component: 'TypeNamed' })
    expect(logService.info).toHaveBeenNthCalledWith(2, 'y', { component: 'Unknown' })
  })
})

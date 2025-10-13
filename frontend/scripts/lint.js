#!/usr/bin/env node
/**
 * Comprehensive linting script for Gene Curator frontend.
 *
 * This script runs all linting tools in the correct order and provides
 * a unified interface for code quality checks.
 */

import { execSync } from 'child_process'
import { fileURLToPath } from 'url'
import { dirname, join } from 'path'

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)
const projectRoot = join(__dirname, '..')

/**
 * Run a command and return success status
 */
function runCommand(cmd, description) {
  console.log(`🔍 ${description}...`)
  try {
    const result = execSync(cmd, {
      cwd: projectRoot,
      stdio: 'pipe',
      encoding: 'utf-8'
    })

    console.log(`✅ ${description} passed`)
    if (result && result.trim()) {
      console.log(`   Output: ${result.trim()}`)
    }
    return true
  } catch (error) {
    console.log(`❌ ${description} failed`)
    if (error.stdout && error.stdout.trim()) {
      console.log(`   stdout: ${error.stdout.trim()}`)
    }
    if (error.stderr && error.stderr.trim()) {
      console.log(`   stderr: ${error.stderr.trim()}`)
    }
    return false
  }
}

function main() {
  console.log('🚀 Starting Gene Curator Frontend Linting Suite')
  console.log('='.repeat(60))

  const checks = [
    ['npm run lint:check', 'ESLint linting'],
    ['npm run format:check', 'Prettier formatting check']
  ]

  const failedChecks = []

  for (const [cmd, description] of checks) {
    if (!runCommand(cmd, description)) {
      failedChecks.push(description)
    }
  }

  console.log(`\n${'='.repeat(60)}`)

  if (failedChecks.length > 0) {
    console.log(`❌ ${failedChecks.length} check(s) failed:`)
    failedChecks.forEach(check => {
      console.log(`   - ${check}`)
    })
    console.log('\n💡 Run individual tools to see detailed error messages:')
    console.log('   - npm run lint:check')
    console.log('   - npm run format:check')
    console.log('\n🔧 Or run fixes:')
    console.log('   - npm run lint (auto-fix ESLint issues)')
    console.log('   - npm run format (auto-format with Prettier)')
    process.exit(1)
  } else {
    console.log('✅ All linting checks passed!')
    console.log('\n🎉 Your code meets all quality standards!')
    process.exit(0)
  }
}

main()

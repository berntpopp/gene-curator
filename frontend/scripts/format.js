#!/usr/bin/env node
/**
 * Auto-formatting script for Gene Curator frontend.
 *
 * This script applies automatic code formatting using ESLint and Prettier.
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
  console.log(`🔧 ${description}...`)
  try {
    const result = execSync(cmd, {
      cwd: projectRoot,
      stdio: 'pipe',
      encoding: 'utf-8'
    })

    console.log(`✅ ${description} completed`)
    if (result && result.trim()) {
      console.log(`   Changes: ${result.trim()}`)
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
  console.log('🎨 Starting Gene Curator Frontend Auto-Formatting')
  console.log('='.repeat(60))

  const formatters = [
    ['npm run format', 'Prettier auto-formatting'],
    ['npm run lint', 'ESLint auto-fixes']
  ]

  const failedFormatters = []

  for (const [cmd, description] of formatters) {
    if (!runCommand(cmd, description)) {
      failedFormatters.push(description)
    }
  }

  console.log(`\n${'='.repeat(60)}`)

  if (failedFormatters.length > 0) {
    console.log(`❌ ${failedFormatters.length} formatter(s) failed:`)
    failedFormatters.forEach(formatter => {
      console.log(`   - ${formatter}`)
    })
    console.log('\n💡 Check the error messages above for details.')
    process.exit(1)
  } else {
    console.log('✅ All formatting completed!')
    console.log('\n💡 Next steps:')
    console.log('   - Run "node scripts/lint.js" to verify formatting')
    console.log('   - Review changes with "git diff"')
    console.log('   - Commit formatted code')
    process.exit(0)
  }
}

main()

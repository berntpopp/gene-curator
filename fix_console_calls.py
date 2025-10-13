#!/usr/bin/env python3
"""
Replace all console.* calls with logger.* calls in Vue files
"""
import re
import os
from pathlib import Path

def fix_vue_file(filepath):
    """Fix console calls in a single Vue file"""
    with open(filepath, 'r') as f:
        content = f.read()

    original_content = content

    # Check if already has useLogger import
    has_use_logger = 'useLogger' in content

    # If has console calls but no useLogger, add import
    if re.search(r'console\.(log|error|warn|info|debug)', content) and not has_use_logger:
        # Find script setup section and add import
        if '<script setup>' in content:
            content = content.replace(
                '<script setup>',
                '<script setup>\nimport { useLogger } from \'@/composables/useLogger\''
            )
        elif '<script>' in content:
            # Find first import and add after it
            match = re.search(r'(import .+ from .+\n)', content)
            if match:
                first_import = match.group(1)
                content = content.replace(
                    first_import,
                    first_import + "import { useLogger } from '@/composables/useLogger'\n"
                )

    # Initialize logger if not already done
    if re.search(r'console\.(log|error|warn|info|debug)', content):
        # Check if logger is initialized
        if 'const logger = useLogger()' not in content and 'const logger=' not in content:
            # Find where to add it - after imports in script setup
            if '<script setup>' in content:
                # Add after all imports
                import_pattern = r'(import .+ from .+\n)+'
                match = re.search(import_pattern, content)
                if match:
                    end_of_imports = match.end()
                    content = content[:end_of_imports] + '\nconst logger = useLogger()\n' + content[end_of_imports:]

    # Replace console calls
    # console.error('message', error) -> logger.error('message', { error: error.message, stack: error.stack })
    content = re.sub(
        r'console\.error\(([^,]+),\s*error\)',
        r'logger.error(\1, { error: error.message, stack: error.stack })',
        content
    )
    content = re.sub(
        r'console\.error\(([^,]+),\s*err\)',
        r'logger.error(\1, { error: err.message, stack: err.stack })',
        content
    )
    content = re.sub(
        r'console\.error\(([^,]+),\s*scopeError\)',
        r'logger.error(\1, { error: scopeError.message, stack: scopeError.stack })',
        content
    )
    content = re.sub(
        r'console\.error\(([^,]+),\s*e\)',
        r'logger.error(\1, { error: e.message, stack: e.stack })',
        content
    )

    # console.warn('message', error) -> logger.warn('message', { error: error.message })
    content = re.sub(
        r'console\.warn\(([^,]+),\s*error\)',
        r'logger.warn(\1, { error: error.message, stack: error.stack })',
        content
    )
    content = re.sub(
        r'console\.warn\(([^,]+),\s*scopeError\)',
        r'logger.warn(\1, { error: scopeError.message, stack: scopeError.stack })',
        content
    )

    # console.log('message') -> logger.info('message')
    content = re.sub(r'console\.log\(', r'logger.info(', content)

    # console.warn with single arg -> logger.warn
    content = re.sub(r'console\.warn\(', r'logger.warn(', content)

    # console.info -> logger.info
    content = re.sub(r'console\.info\(', r'logger.info(', content)

    # console.debug -> logger.debug
    content = re.sub(r'console\.debug\(', r'logger.debug(', content)

    # Only write if changed
    if content != original_content:
        with open(filepath, 'w') as f:
            f.write(content)
        return True
    return False

def main():
    """Find and fix all Vue files"""
    frontend_src = Path('/home/bernt-popp/development/gene-curator/frontend/src')

    vue_files = list(frontend_src.rglob('*.vue'))

    fixed_count = 0
    for vue_file in vue_files:
        # Skip node_modules
        if 'node_modules' in str(vue_file):
            continue

        try:
            if fix_vue_file(vue_file):
                print(f"Fixed: {vue_file.relative_to(frontend_src)}")
                fixed_count += 1
        except Exception as e:
            print(f"Error processing {vue_file}: {e}")

    print(f"\nFixed {fixed_count} files")

if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""
Script to add CSRF tokens to all forms in templates
"""
import os
import re

# Templates directory
templates_dir = 'templates'

# CSRF token line to add
csrf_token_line = '                    <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">'

def add_csrf_to_file(filepath):
    """Add CSRF tokens to forms in a template file"""
    with open(filepath, 'r') as f:
        content = f.read()

    # Skip if file already has csrf_token
    if 'csrf_token()' in content:
        print(f"  Skipping {filepath} - already has CSRF tokens")
        return False

    # Pattern to match form tags
    # Matches: <form method="POST" ...>
    pattern = r'(<form\s+method=["\']POST["\'][^>]*>)'

    def add_csrf(match):
        form_tag = match.group(1)
        # Calculate indentation from the form tag
        lines_before = content[:match.start()].split('\n')
        last_line = lines_before[-1] if lines_before else ''
        indent = ' ' * (len(last_line) - len(last_line.lstrip()))

        # Add CSRF token after form tag
        return f'{form_tag}\n{indent}    <input type="hidden" name="csrf_token" value="{{{{ csrf_token() }}}}">'

    # Replace all form tags
    new_content, count = re.subn(pattern, add_csrf, content)

    if count > 0:
        with open(filepath, 'w') as f:
            f.write(new_content)
        print(f"  Added CSRF tokens to {count} forms in {filepath}")
        return True
    else:
        print(f"  No POST forms found in {filepath}")
        return False

def main():
    print("Adding CSRF tokens to all template forms...")
    print("=" * 60)

    updated_count = 0

    # Process all HTML files in templates directory
    for filename in os.listdir(templates_dir):
        if filename.endswith('.html'):
            filepath = os.path.join(templates_dir, filename)
            if add_csrf_to_file(filepath):
                updated_count += 1

    print("=" * 60)
    print(f"\nUpdated {updated_count} template files with CSRF tokens")
    print("\nNote: Some templates may have been skipped if they already had CSRF tokens")

if __name__ == '__main__':
    main()

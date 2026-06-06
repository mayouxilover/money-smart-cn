#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fix article dates from 2025 to 2026
"""

import os
import re

# Use Windows path format
posts_dir = r"C:\Users\Administrator\WorkBuddy\2026-06-06-01-17-09\_posts"

# Get all md files starting with 2025-
files = [f for f in os.listdir(posts_dir) if f.startswith("2025-") and f.endswith(".md")]

print(f"Found {len(files)} files with 2025- dates")

for filename in sorted(files):
    old_path = os.path.join(posts_dir, filename)
    
    # New filename: replace 2025- with 2026-
    new_filename = filename.replace("2025-", "2026-")
    new_path = os.path.join(posts_dir, new_filename)
    
    # Read file content
    with open(old_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Replace date in frontmatter: 2025- to 2026-
    content = re.sub(r'(date:\s*)2025-', r'\g<1>2026-', content)
    
    # Write to new filename
    with open(new_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    # Remove old file
    os.remove(old_path)
    
    print(f"Renamed: {filename} -> {new_filename}")

print(f"\nDone! Fixed {len(files)} articles.")

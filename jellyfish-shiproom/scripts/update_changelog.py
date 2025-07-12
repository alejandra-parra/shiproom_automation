#!/usr/bin/env python3
"""
Helper script to add new entries to the CHANGELOG.md file.
Usage: python scripts/update_changelog.py --type added --message "New feature description"
"""

import argparse
import re
from datetime import datetime
from pathlib import Path

def add_changelog_entry(entry_type: str, message: str, version: str = "jellyfish-shiproom v1.1.0"):
    """
    Add a new entry to the CHANGELOG.md file.
    
    Args:
        entry_type: Type of change (added, changed, fixed, removed, etc.)
        message: Description of the change
        version: Version to add the entry to (default: "Unreleased")
    """
    changelog_path = Path("CHANGELOG.md")
    
    if not changelog_path.exists():
        print("Error: CHANGELOG.md not found in current directory")
        return
    
    # Read the current changelog
    with open(changelog_path, 'r') as f:
        content = f.read()
    
    # Find the section for the specified version
    version_pattern = rf"## \[{re.escape(version)}\]"
    match = re.search(version_pattern, content)
    
    if not match:
        print(f"Error: Version '{version}' not found in changelog")
        return
    
    # Find the section for the entry type
    section_pattern = rf"### {entry_type.capitalize()}\n"
    section_match = re.search(section_pattern, content[match.start():])
    
    if section_match:
        # Section exists, add entry to it
        section_start = match.start() + section_match.end()
        # Find the next section or end of version block
        next_section = re.search(r"\n### [A-Z]", content[section_start:])
        if next_section:
            insert_pos = section_start + next_section.start()
        else:
            # No next section, add before the next version or end of file
            next_version = re.search(r"\n## \[", content[section_start:])
            if next_version:
                insert_pos = section_start + next_version.start()
            else:
                insert_pos = len(content)
        
        new_entry = f"- {message}\n"
        content = content[:insert_pos] + new_entry + content[insert_pos:]
    else:
        # Section doesn't exist, create it
        # Find where to insert the new section (after the version header)
        version_end = match.end()
        next_section = re.search(r"\n### [A-Z]", content[version_end:])
        
        if next_section:
            insert_pos = version_end + next_section.start()
        else:
            # No sections yet, add after version header
            insert_pos = version_end
        
        new_section = f"\n### {entry_type.capitalize()}\n- {message}\n"
        content = content[:insert_pos] + new_section + content[insert_pos:]
    
    # Write the updated changelog
    with open(changelog_path, 'w') as f:
        f.write(content)
    
    print(f"✅ Added '{entry_type}' entry to CHANGELOG.md under version '{version}'")
    print(f"   Message: {message}")

def main():
    parser = argparse.ArgumentParser(description="Add entry to CHANGELOG.md")
    parser.add_argument("--type", required=True, 
                       choices=["added", "changed", "deprecated", "removed", "fixed", "security"],
                       help="Type of change")
    parser.add_argument("--message", required=True, 
                       help="Description of the change")
    parser.add_argument("--version", default="jellyfish-shiproom v1.1.0",
                       help="Version to add entry to (default: jellyfish-shiproom v1.1.0)")
    
    args = parser.parse_args()
    add_changelog_entry(args.type, args.message, args.version)

if __name__ == "__main__":
    main() 
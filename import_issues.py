#!/usr/bin/env python3
"""
Import GitHub Issues to Local Tracker

This script helps you manually import GitHub issues into the local ISSUES.md file.
"""

import re
from pathlib import Path


def parse_issue_text(issue_text):
    """Parse issue text and extract structured information."""
    lines = issue_text.strip().split('\n')
    issues = []
    
    current_issue = None
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Look for issue pattern: #123 Title
        issue_match = re.match(r'#(\d+)\s+(.+)', line)
        if issue_match:
            if current_issue:
                issues.append(current_issue)
            
            current_issue = {
                'number': int(issue_match.group(1)),
                'title': issue_match.group(2),
                'labels': [],
                'description': '',
                'priority': 'Medium',
                'type': 'Enhancement'
            }
        elif current_issue and line.startswith('Labels:'):
            # Extract labels
            labels_text = line.replace('Labels:', '').strip()
            current_issue['labels'] = [l.strip() for l in labels_text.split(',') if l.strip()]
            
            # Determine type and priority from labels
            for label in current_issue['labels']:
                if label.lower() in ['bug', 'bugfix']:
                    current_issue['type'] = 'Bug'
                elif label.lower() in ['enhancement', 'feature']:
                    current_issue['type'] = 'Enhancement'
                elif label.lower() in ['documentation', 'docs']:
                    current_issue['type'] = 'Documentation'
                elif label.lower() in ['testing', 'test']:
                    current_issue['type'] = 'Testing'
                elif label.lower() in ['high priority', 'critical']:
                    current_issue['priority'] = 'High'
                elif label.lower() in ['low priority']:
                    current_issue['priority'] = 'Low'
        elif current_issue:
            # Add to description
            if current_issue['description']:
                current_issue['description'] += ' '
            current_issue['description'] += line
    
    if current_issue:
        issues.append(current_issue)
    
    return issues


def update_issues_file(issues):
    """Update the ISSUES.md file with parsed issues."""
    issues_file = Path('ISSUES.md')
    
    # Group issues by type and priority
    bugs = {'High': [], 'Medium': [], 'Low': []}
    enhancements = {'High': [], 'Medium': [], 'Low': []}
    docs = []
    testing = []
    infrastructure = []
    
    for issue in issues:
        if issue['type'] == 'Bug':
            bugs[issue['priority']].append(issue)
        elif issue['type'] == 'Enhancement':
            enhancements[issue['priority']].append(issue)
        elif issue['type'] == 'Documentation':
            docs.append(issue)
        elif issue['type'] == 'Testing':
            testing.append(issue)
        else:
            infrastructure.append(issue)
    
    # Generate new content
    content = """# HydroSim Issues Tracker

## 🐛 Bug Fixes

"""
    
    for priority in ['High', 'Medium', 'Low']:
        if bugs[priority]:
            content += f"### {priority} Priority\n"
            for issue in bugs[priority]:
                labels_str = ', '.join(issue['labels']) if issue['labels'] else 'None'
                content += f"""- [ ] **Issue #{issue['number']}**: {issue['title']}
  - **Status**: Open
  - **Priority**: {priority}
  - **Labels**: {labels_str}
  - **Assignee**: 
  - **Branch**: 
  - **Notes**: {issue['description'][:100]}{'...' if len(issue['description']) > 100 else ''}

"""
    
    content += """## ✨ Enhancements

"""
    
    for priority in ['High', 'Medium', 'Low']:
        if enhancements[priority]:
            content += f"### {priority} Priority\n"
            for issue in enhancements[priority]:
                labels_str = ', '.join(issue['labels']) if issue['labels'] else 'None'
                content += f"""- [ ] **Issue #{issue['number']}**: {issue['title']}
  - **Status**: Open
  - **Priority**: {priority}
  - **Labels**: {labels_str}
  - **Assignee**: 
  - **Branch**: 
  - **Notes**: {issue['description'][:100]}{'...' if len(issue['description']) > 100 else ''}

"""
    
    if docs:
        content += """## 📚 Documentation

"""
        for issue in docs:
            labels_str = ', '.join(issue['labels']) if issue['labels'] else 'None'
            content += f"""- [ ] **Issue #{issue['number']}**: {issue['title']}
  - **Status**: Open
  - **Labels**: {labels_str}
  - **Assignee**: 
  - **Branch**: 
  - **Notes**: {issue['description'][:100]}{'...' if len(issue['description']) > 100 else ''}

"""
    
    if testing:
        content += """## 🧪 Testing

"""
        for issue in testing:
            labels_str = ', '.join(issue['labels']) if issue['labels'] else 'None'
            content += f"""- [ ] **Issue #{issue['number']}**: {issue['title']}
  - **Status**: Open
  - **Labels**: {labels_str}
  - **Assignee**: 
  - **Branch**: 
  - **Notes**: {issue['description'][:100]}{'...' if len(issue['description']) > 100 else ''}

"""
    
    if infrastructure:
        content += """## 🔧 Infrastructure

"""
        for issue in infrastructure:
            labels_str = ', '.join(issue['labels']) if issue['labels'] else 'None'
            content += f"""- [ ] **Issue #{issue['number']}**: {issue['title']}
  - **Status**: Open
  - **Labels**: {labels_str}
  - **Assignee**: 
  - **Branch**: 
  - **Notes**: {issue['description'][:100]}{'...' if len(issue['description']) > 100 else ''}

"""
    
    content += """---

## Issue Template

When adding new issues, use this template:

```markdown
- [ ] **Issue #X**: [Brief description]
  - **Status**: Open/In Progress/Review/Closed
  - **Priority**: High/Medium/Low
  - **Type**: Bug/Enhancement/Documentation/Testing/Infrastructure
  - **Assignee**: [Your name or team member]
  - **Branch**: [feature/issue-X-description or bugfix/issue-X-description]
  - **Estimated Time**: [hours/days]
  - **Dependencies**: [Other issues this depends on]
  - **Notes**: [Additional context, links, etc.]
```

## Status Definitions

- **Open**: Issue identified, not yet started
- **In Progress**: Actively being worked on
- **Review**: Code complete, needs review/testing
- **Closed**: Issue resolved and merged

## Priority Guidelines

- **High**: Critical bugs, security issues, blocking other work
- **Medium**: Important features, non-critical bugs, performance improvements
- **Low**: Nice-to-have features, code cleanup, minor improvements"""
    
    # Write to file
    issues_file.write_text(content)
    print(f"✅ Updated {issues_file} with {len(issues)} issues")
    
    return len(issues)


def main():
    print("🔄 GitHub Issues Importer")
    print("=" * 50)
    print()
    print("Please copy and paste your GitHub issues here.")
    print("Format each issue as:")
    print("  #123 Issue Title")
    print("  Labels: bug, high priority")
    print("  Description of the issue...")
    print()
    print("Paste all issues, then press Ctrl+D (or Ctrl+Z on Windows) when done:")
    print()
    
    # Read all input
    try:
        issue_text = ""
        while True:
            try:
                line = input()
                issue_text += line + "\n"
            except EOFError:
                break
    except KeyboardInterrupt:
        print("\n❌ Import cancelled")
        return
    
    if not issue_text.strip():
        print("❌ No issues provided")
        return
    
    # Parse issues
    print("\n🔄 Parsing issues...")
    issues = parse_issue_text(issue_text)
    
    if not issues:
        print("❌ No valid issues found")
        print("Make sure to use the format: #123 Issue Title")
        return
    
    print(f"✅ Found {len(issues)} issues:")
    for issue in issues:
        print(f"  - #{issue['number']}: {issue['title']} ({issue['type']}, {issue['priority']})")
    
    # Update ISSUES.md
    print("\n🔄 Updating ISSUES.md...")
    count = update_issues_file(issues)
    
    print(f"\n🎉 Successfully imported {count} issues!")
    print("Next steps:")
    print("1. Review ISSUES.md")
    print("2. Choose an issue to work on")
    print("3. Run: python dev_tools.py start <issue_number> <type> '<description>'")


if __name__ == "__main__":
    main()
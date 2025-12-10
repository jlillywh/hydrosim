#!/usr/bin/env python3
"""
Fetch GitHub Issues Automatically

This script fetches issues from your GitHub repository using the GitHub API
and updates the local ISSUES.md file automatically.
"""

import requests
import json
from pathlib import Path
import sys


def fetch_github_issues(repo_owner, repo_name):
    """Fetch issues from GitHub API."""
    url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/issues"
    
    print(f"🔄 Fetching issues from {repo_owner}/{repo_name}...")
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        
        issues = response.json()
        print(f"✅ Found {len(issues)} issues")
        
        return issues
    
    except requests.exceptions.RequestException as e:
        print(f"❌ Error fetching issues: {e}")
        return None


def categorize_issue(issue):
    """Categorize issue based on labels."""
    labels = [label['name'].lower() for label in issue.get('labels', [])]
    
    # Determine type
    issue_type = 'Enhancement'  # default
    if any(label in labels for label in ['bug', 'bugfix', 'error']):
        issue_type = 'Bug'
    elif any(label in labels for label in ['documentation', 'docs']):
        issue_type = 'Documentation'
    elif any(label in labels for label in ['testing', 'test', 'tests']):
        issue_type = 'Testing'
    elif any(label in labels for label in ['infrastructure', 'ci', 'build']):
        issue_type = 'Infrastructure'
    
    # Determine priority
    priority = 'Medium'  # default
    if any(label in labels for label in ['high priority', 'critical', 'urgent']):
        priority = 'High'
    elif any(label in labels for label in ['low priority', 'nice to have']):
        priority = 'Low'
    
    return issue_type, priority


def format_issue_for_markdown(issue):
    """Format a GitHub issue for our ISSUES.md format."""
    number = issue['number']
    title = issue['title']
    body = issue.get('body', '') or ''
    labels = [label['name'] for label in issue.get('labels', [])]
    state = issue['state']
    
    issue_type, priority = categorize_issue(issue)
    
    # Truncate body for notes
    notes = body.replace('\n', ' ').replace('\r', ' ')[:200]
    if len(body) > 200:
        notes += '...'
    
    labels_str = ', '.join(labels) if labels else 'None'
    
    status = 'Open' if state == 'open' else 'Closed'
    
    return {
        'number': number,
        'title': title,
        'type': issue_type,
        'priority': priority,
        'status': status,
        'labels': labels_str,
        'notes': notes,
        'url': issue['html_url']
    }


def update_issues_file(issues):
    """Update ISSUES.md with fetched GitHub issues."""
    if not issues:
        print("❌ No issues to process")
        return
    
    # Format all issues
    formatted_issues = [format_issue_for_markdown(issue) for issue in issues]
    
    # Group by type and priority
    bugs = {'High': [], 'Medium': [], 'Low': []}
    enhancements = {'High': [], 'Medium': [], 'Low': []}
    docs = []
    testing = []
    infrastructure = []
    
    for issue in formatted_issues:
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
    
    # Generate markdown content
    content = f"""# HydroSim Issues Tracker

*Last updated: Automatically synced from GitHub*

## 🐛 Bug Fixes

"""
    
    # Add bugs by priority
    for priority in ['High', 'Medium', 'Low']:
        if bugs[priority]:
            content += f"### {priority} Priority\n"
            for issue in bugs[priority]:
                checkbox = '- [x]' if issue['status'] == 'Closed' else '- [ ]'
                content += f"""{checkbox} **Issue #{issue['number']}**: {issue['title']}
  - **Status**: {issue['status']}
  - **Priority**: {priority}
  - **Labels**: {issue['labels']}
  - **GitHub**: {issue['url']}
  - **Assignee**: 
  - **Branch**: 
  - **Notes**: {issue['notes']}

"""
    
    # Add enhancements
    content += """## ✨ Enhancements

"""
    
    for priority in ['High', 'Medium', 'Low']:
        if enhancements[priority]:
            content += f"### {priority} Priority\n"
            for issue in enhancements[priority]:
                checkbox = '- [x]' if issue['status'] == 'Closed' else '- [ ]'
                content += f"""{checkbox} **Issue #{issue['number']}**: {issue['title']}
  - **Status**: {issue['status']}
  - **Priority**: {priority}
  - **Labels**: {issue['labels']}
  - **GitHub**: {issue['url']}
  - **Assignee**: 
  - **Branch**: 
  - **Notes**: {issue['notes']}

"""
    
    # Add other categories
    if docs:
        content += """## 📚 Documentation

"""
        for issue in docs:
            checkbox = '- [x]' if issue['status'] == 'Closed' else '- [ ]'
            content += f"""{checkbox} **Issue #{issue['number']}**: {issue['title']}
  - **Status**: {issue['status']}
  - **Labels**: {issue['labels']}
  - **GitHub**: {issue['url']}
  - **Assignee**: 
  - **Branch**: 
  - **Notes**: {issue['notes']}

"""
    
    if testing:
        content += """## 🧪 Testing

"""
        for issue in testing:
            checkbox = '- [x]' if issue['status'] == 'Closed' else '- [ ]'
            content += f"""{checkbox} **Issue #{issue['number']}**: {issue['title']}
  - **Status**: {issue['status']}
  - **Labels**: {issue['labels']}
  - **GitHub**: {issue['url']}
  - **Assignee**: 
  - **Branch**: 
  - **Notes**: {issue['notes']}

"""
    
    if infrastructure:
        content += """## 🔧 Infrastructure

"""
        for issue in infrastructure:
            checkbox = '- [x]' if issue['status'] == 'Closed' else '- [ ]'
            content += f"""{checkbox} **Issue #{issue['number']}**: {issue['title']}
  - **Status**: {issue['status']}
  - **Labels**: {issue['labels']}
  - **GitHub**: {issue['url']}
  - **Assignee**: 
  - **Branch**: 
  - **Notes**: {issue['notes']}

"""
    
    # Add footer
    content += """---

## Development Workflow

To work on an issue:

```bash
# Start working on issue
python dev_tools.py start <issue_number> <type> "<description>"

# Example:
python dev_tools.py start 1 bugfix "fix temperature validation"
python dev_tools.py start 2 feature "add uncertainty analysis"
```

## Issue Types for dev_tools.py

- `bugfix` - For bug fixes
- `feature` - For new features/enhancements  
- `docs` - For documentation improvements
- `test` - For testing improvements

## Sync with GitHub

To refresh this file with latest GitHub issues:

```bash
python fetch_github_issues.py
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
    issues_file = Path('ISSUES.md')
    issues_file.write_text(content, encoding='utf-8')
    
    print(f"✅ Updated {issues_file} with {len(formatted_issues)} issues")
    
    # Print summary
    print("\n📊 Issue Summary:")
    total_open = sum(1 for issue in formatted_issues if issue['status'] == 'Open')
    total_closed = sum(1 for issue in formatted_issues if issue['status'] == 'Closed')
    print(f"  Open: {total_open}")
    print(f"  Closed: {total_closed}")
    print(f"  Total: {len(formatted_issues)}")
    
    print("\n🏷️  By Type:")
    type_counts = {}
    for issue in formatted_issues:
        type_counts[issue['type']] = type_counts.get(issue['type'], 0) + 1
    for issue_type, count in sorted(type_counts.items()):
        print(f"  {issue_type}: {count}")


def main():
    """Main function."""
    print("🔄 GitHub Issues Fetcher")
    print("=" * 50)
    
    # Repository info - automatically detected from git remote
    try:
        import subprocess
        result = subprocess.run(['git', 'remote', 'get-url', 'origin'], 
                              capture_output=True, text=True, check=True)
        remote_url = result.stdout.strip()
        
        # Parse GitHub URL
        if 'github.com' in remote_url:
            if remote_url.startswith('git@github.com:'):
                # SSH format: git@github.com:owner/repo.git
                repo_path = remote_url.replace('git@github.com:', '').replace('.git', '')
            elif remote_url.startswith('https://github.com/'):
                # HTTPS format: https://github.com/owner/repo.git
                repo_path = remote_url.replace('https://github.com/', '').replace('.git', '')
            else:
                raise ValueError("Unknown GitHub URL format")
            
            repo_owner, repo_name = repo_path.split('/')
            print(f"📍 Repository: {repo_owner}/{repo_name}")
            
        else:
            raise ValueError("Not a GitHub repository")
            
    except Exception as e:
        print(f"❌ Could not detect repository: {e}")
        print("Please run this script from your HydroSim repository directory")
        return 1
    
    # Fetch issues
    issues = fetch_github_issues(repo_owner, repo_name)
    if issues is None:
        return 1
    
    # Update ISSUES.md
    update_issues_file(issues)
    
    print(f"\n🎉 Successfully synced GitHub issues!")
    print("Next steps:")
    print("1. Review ISSUES.md")
    print("2. Choose an issue: python dev_tools.py start <number> <type> '<description>'")
    print("3. Make your changes and test")
    print("4. Finish: python dev_tools.py finish <number>")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
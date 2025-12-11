#!/usr/bin/env python3
"""
Fetch Issue #1 details from GitHub API.
"""

import requests
import os

def fetch_github_issue(issue_number):
    """Fetch GitHub issue details."""
    
    # GitHub repository info
    owner = "jlillywh"
    repo = "hydrosim"
    
    # Try to get GitHub token from environment
    token = os.getenv('GITHUB_TOKEN')
    headers = {}
    if token:
        headers = {
            'Authorization': f'token {token}',
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'HydroSim-Issue-Fetcher'
        }
    
    # Fetch the issue
    url = f'https://api.github.com/repos/{owner}/{repo}/issues/{issue_number}'
    
    print(f"📥 Fetching issue #{issue_number}...")
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        issue = response.json()
        print(f"✅ Issue #{issue_number} fetched successfully!")
        print(f"Title: {issue['title']}")
        print(f"State: {issue['state']}")
        print(f"URL: {issue['html_url']}")
        print("\nDescription:")
        print("=" * 60)
        print(issue['body'])
        print("=" * 60)
        return issue
    else:
        print(f"❌ Failed to fetch issue: {response.status_code}")
        print(response.text)
        return None

if __name__ == "__main__":
    fetch_github_issue(1)
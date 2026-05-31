"""Fetch PR data from GitHub API."""

from datetime import datetime, timedelta, timezone

import requests

from .config import GITHUB_TOKEN, SGLANG_REPO

API_BASE = "https://api.github.com"
HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}


def _get(url, params=None):
    """Make a paginated GET request to GitHub API."""
    results = []
    params = params or {}
    params.setdefault("per_page", 100)
    while url:
        resp = requests.get(url, headers=HEADERS, params=params)
        resp.raise_for_status()
        results.extend(resp.json())
        url = resp.links.get("next", {}).get("url")
        params = None
    return results


def get_report_window():
    """Compute the exact reporting window: last Sunday 00:00 UTC to this Sunday 00:00 UTC.

    This ensures no overlap or gaps between consecutive weekly reports.
    """
    now = datetime.now(timezone.utc)
    days_since_sunday = (now.weekday() + 1) % 7
    end = now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=days_since_sunday)
    start = end - timedelta(days=7)
    return start, end


def get_merged_prs(repo=None):
    """Fetch PRs merged in the reporting window (Sunday-to-Sunday UTC)."""
    repo = repo or SGLANG_REPO
    start, end = get_report_window()
    query = f"repo:{repo} is:pr is:merged merged:{start.strftime('%Y-%m-%d')}..{end.strftime('%Y-%m-%d')}"
    url = f"{API_BASE}/search/issues"
    params = {"q": query, "sort": "updated", "order": "desc", "per_page": 100}

    all_items = []
    resp = requests.get(url, headers=HEADERS, params=params)
    resp.raise_for_status()
    data = resp.json()
    all_items.extend(data.get("items", []))

    while "next" in resp.links:
        resp = requests.get(resp.links["next"]["url"], headers=HEADERS)
        resp.raise_for_status()
        all_items.extend(resp.json().get("items", []))

    return all_items


def get_open_prs_under_review(repo=None):
    """Fetch open PRs that have review activity (limited to recently updated)."""
    repo = repo or SGLANG_REPO
    since = (datetime.now(timezone.utc) - timedelta(days=14)).isoformat()
    query = f"repo:{repo} is:pr is:open updated:>={since} comments:>0"
    url = f"{API_BASE}/search/issues"
    params = {"q": query, "sort": "comments", "order": "desc", "per_page": 100}

    all_items = []
    resp = requests.get(url, headers=HEADERS, params=params)
    resp.raise_for_status()
    data = resp.json()
    all_items.extend(data.get("items", []))

    while "next" in resp.links and len(all_items) < 200:
        resp = requests.get(resp.links["next"]["url"], headers=HEADERS)
        resp.raise_for_status()
        all_items.extend(resp.json().get("items", []))

    return all_items


def get_pr_details(pr_number, repo=None):
    """Get full PR details including diff stats."""
    repo = repo or SGLANG_REPO
    url = f"{API_BASE}/repos/{repo}/pulls/{pr_number}"
    resp = requests.get(url, headers=HEADERS)
    resp.raise_for_status()
    return resp.json()


def get_pr_reviews(pr_number, repo=None):
    """Get reviews for a PR."""
    repo = repo or SGLANG_REPO
    url = f"{API_BASE}/repos/{repo}/pulls/{pr_number}/reviews"
    return _get(url)


def get_pr_review_comments(pr_number, repo=None):
    """Get review comments (inline code comments) for a PR."""
    repo = repo or SGLANG_REPO
    url = f"{API_BASE}/repos/{repo}/pulls/{pr_number}/comments"
    return _get(url)


def get_pr_diff(pr_number, repo=None):
    """Get the diff for a PR (truncated for large PRs)."""
    repo = repo or SGLANG_REPO
    url = f"{API_BASE}/repos/{repo}/pulls/{pr_number}"
    headers = {**HEADERS, "Accept": "application/vnd.github.v3.diff"}
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    diff = resp.text
    if len(diff) > 15000:
        diff = diff[:15000] + "\n... [truncated]"
    return diff


def get_user_org(username, repo=None):
    """Infer organization from user's recent commits or profile."""
    repo = repo or SGLANG_REPO

    url = f"{API_BASE}/users/{username}/orgs"
    resp = requests.get(url, headers=HEADERS)
    if resp.status_code == 200:
        orgs = resp.json()
        if orgs:
            return orgs[0].get("login", "Unknown")

    url = f"{API_BASE}/users/{username}"
    resp = requests.get(url, headers=HEADERS)
    if resp.status_code == 200:
        user_data = resp.json()
        company = user_data.get("company")
        if company:
            return company.lstrip("@")

    url = f"{API_BASE}/repos/{repo}/commits"
    params = {"author": username, "per_page": 5}
    resp = requests.get(url, headers=HEADERS, params=params)
    if resp.status_code == 200:
        commits = resp.json()
        for commit in commits:
            email = commit.get("commit", {}).get("author", {}).get("email", "")
            if email and "@" in email:
                domain = email.split("@")[1]
                if domain not in ("gmail.com", "users.noreply.github.com", "outlook.com", "hotmail.com", "yahoo.com"):
                    return domain.split(".")[0].capitalize()

    return "Independent"


def get_top_reviewers(merged_prs, top_n=5, repo=None):
    """Find the top N reviewers who approved the most merged PRs."""
    repo = repo or SGLANG_REPO
    from collections import Counter
    reviewer_counts = Counter()

    for pr in merged_prs:
        pr_number = pr["number"]
        try:
            reviews = get_pr_reviews(pr_number, repo=repo)
            seen = set()
            for review in reviews:
                user = review.get("user", {}).get("login", "")
                state = review.get("state", "")
                if user and state == "APPROVED" and user not in seen:
                    reviewer_counts[user] += 1
                    seen.add(user)
        except Exception:
            continue

    return reviewer_counts.most_common(top_n)

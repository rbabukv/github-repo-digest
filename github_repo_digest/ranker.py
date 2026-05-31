"""Rank PRs by code size, impact, reviewers, and review comments."""

from .github_client import get_pr_details, get_pr_reviews, get_pr_review_comments


def enrich_pr(pr_item, repo=None):
    """Enrich a PR search result with detailed stats for ranking."""
    pr_number = pr_item["number"]

    details = get_pr_details(pr_number, repo=repo)
    reviews = get_pr_reviews(pr_number, repo=repo)
    review_comments = get_pr_review_comments(pr_number, repo=repo)

    unique_reviewers = set()
    for review in reviews:
        if review.get("user", {}).get("login"):
            unique_reviewers.add(review["user"]["login"])

    additions = details.get("additions", 0)
    deletions = details.get("deletions", 0)
    changed_files = details.get("changed_files", 0)

    pr_item["_additions"] = additions
    pr_item["_deletions"] = deletions
    pr_item["_changed_files"] = changed_files
    pr_item["_code_size"] = additions + deletions
    pr_item["_num_reviewers"] = len(unique_reviewers)
    pr_item["_num_review_comments"] = len(review_comments)
    pr_item["_reviewers"] = list(unique_reviewers)
    pr_item["_details"] = details

    return pr_item


def compute_impact_score(pr):
    """Heuristic impact score based on files changed, labels, and title keywords."""
    score = 0
    score += min(pr["_changed_files"] * 2, 40)

    high_impact_keywords = ["breaking", "perf", "optimization", "major", "refactor", "arch"]
    title = pr.get("title", "").lower()
    for kw in high_impact_keywords:
        if kw in title:
            score += 15

    labels = [l.get("name", "").lower() for l in pr.get("labels", [])]
    for label in labels:
        if any(kw in label for kw in ("high-priority", "critical", "breaking", "performance")):
            score += 20

    return score


def pre_filter(prs, top_n=80):
    """Pre-filter PRs using search-API metadata (comments count) to reduce API calls."""
    for pr in prs:
        pr["_pre_score"] = pr.get("comments", 0)

    prs.sort(key=lambda p: p["_pre_score"], reverse=True)
    return prs[:top_n]


def rank_prs(prs, top_n=40, repo=None):
    """Rank PRs by: code size > impact > reviewers > review comments.

    Pre-filters to top_n*2 by comment activity before enriching (to reduce API calls).
    """
    candidates = pre_filter(prs, top_n=top_n * 2)

    enriched = []
    for i, pr in enumerate(candidates):
        try:
            enriched.append(enrich_pr(pr, repo=repo))
            if (i + 1) % 10 == 0:
                print(f"      Enriched {i + 1}/{len(candidates)} PRs...")
        except Exception as e:
            print(f"      Skipping PR #{pr.get('number', '?')}: {e}")
            continue

    for pr in enriched:
        pr["_impact_score"] = compute_impact_score(pr)

    enriched.sort(key=lambda p: (
        p["_code_size"],
        p["_impact_score"],
        p["_num_reviewers"],
        p["_num_review_comments"],
    ), reverse=True)

    return enriched[:top_n]

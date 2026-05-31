"""Main entry point for GitHub Repo Digest agent."""

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

import schedule
import time

from jinja2 import Environment, FileSystemLoader

from .config import TOP_N_PRS, SCHEDULE_CRON, SCHEDULE_DAY, SGLANG_REPO
from .github_client import get_merged_prs, get_open_prs_under_review, get_user_org, get_report_window
from .ranker import rank_prs
from .summarizer import batch_summarize
from .emailer import send_digest


def get_week_label():
    """Get work-week label like Ww22."""
    now = datetime.now(timezone.utc)
    week_num = now.isocalendar()[1]
    return f"Ww{week_num:02d}"


def get_date_range(repo):
    """Get human-readable date range matching the exact reporting window."""
    start, end = get_report_window()
    return f"{start.strftime('%b %d')} — {end.strftime('%b %d, %Y')}"


def get_repo_short_name(repo):
    """Extract short name from owner/repo format."""
    return repo.split("/")[-1] if "/" in repo else repo


def generate_digest(dry_run=False, output_file=None, repo=None):
    """Generate and send the weekly digest."""
    repo = repo or SGLANG_REPO
    repo_name = get_repo_short_name(repo)

    start, end = get_report_window()
    print(f"📦 Repository: {repo}")
    print(f"📅 Report window: {start.strftime('%Y-%m-%d %H:%M UTC')} → {end.strftime('%Y-%m-%d %H:%M UTC')}")

    print("📥 Fetching merged PRs...")
    merged_prs_raw = get_merged_prs(repo=repo)
    print(f"   Found {len(merged_prs_raw)} merged PRs")

    print("📥 Fetching open PRs under review...")
    open_prs_raw = get_open_prs_under_review(repo=repo)
    print(f"   Found {len(open_prs_raw)} open PRs")

    print(f"📊 Ranking and enriching top {TOP_N_PRS} merged PRs...")
    merged_ranked = rank_prs(merged_prs_raw, top_n=TOP_N_PRS, repo=repo)
    print(f"   Enriched {len(merged_ranked)} merged PRs")

    print(f"📊 Ranking and enriching top {TOP_N_PRS} open PRs...")
    open_ranked = rank_prs(open_prs_raw, top_n=TOP_N_PRS, repo=repo)
    print(f"   Enriched {len(open_ranked)} open PRs")

    print("🤖 Generating AI summaries for merged PRs...")
    merged_summaries = batch_summarize(merged_ranked)

    print("🤖 Generating AI summaries for open PRs...")
    open_summaries = batch_summarize(open_ranked)

    print("🏢 Resolving author organizations...")
    org_cache = {}
    for pr in merged_ranked + open_ranked:
        username = pr.get("user", {}).get("login", "")
        if username and username not in org_cache:
            org_cache[username] = get_user_org(username, repo=repo)
        pr["org"] = org_cache.get(username, "Unknown")
        pr["ai_summary"] = merged_summaries.get(pr["number"]) or open_summaries.get(pr["number"], "")

    week_label = get_week_label()
    subject = f"{repo_name.capitalize()} Summary Digest — {week_label}"

    template_dir = Path(__file__).parent / "templates"
    env = Environment(loader=FileSystemLoader(str(template_dir)))
    template = env.get_template("digest.html")

    html = template.render(
        repo_name=repo_name,
        repo_full=repo,
        week_label=week_label,
        generated_date=datetime.now(timezone.utc).strftime("%B %d, %Y at %H:%M UTC"),
        date_range=get_date_range(repo),
        report_start=start.strftime("%b %d, %Y %H:%M UTC"),
        report_end=end.strftime("%b %d, %Y %H:%M UTC"),
        total_merged=len(merged_prs_raw),
        total_open_under_review=len(open_prs_raw),
        merged_prs=merged_ranked,
        open_prs=open_ranked,
    )

    if output_file:
        Path(output_file).write_text(html)
        print(f"💾 HTML saved to {output_file}")

    if dry_run:
        print(f"🏁 Dry run complete. Subject: {subject}")
        print(f"   Merged PRs: {len(merged_ranked)}, Open PRs: {len(open_ranked)}")
        return

    print(f"📧 Sending email: {subject}")
    send_digest(subject, html)
    print("✅ Digest sent successfully!")


def run_daemon(repo=None):
    """Run as a daemon, sending digest on schedule."""
    hour, minute = SCHEDULE_CRON.split(":")
    schedule_time = f"{hour}:{minute}"

    job = getattr(schedule.every(), SCHEDULE_DAY)
    job.at(schedule_time).do(generate_digest, repo=repo)

    print(f"⏰ Scheduled: every {SCHEDULE_DAY} at {schedule_time} UTC")
    print("   (Monday 01:30 UTC = Monday 07:00 IST)")
    print("   Press Ctrl+C to stop")

    while True:
        schedule.run_pending()
        time.sleep(60)


def main():
    parser = argparse.ArgumentParser(
        description="GitHub Repo Digest — AI-powered weekly PR summary agent"
    )
    parser.add_argument(
        "--repo", type=str, default=None,
        help="GitHub repo in owner/name format (default: sgl-project/sglang)"
    )
    parser.add_argument(
        "--run-now", action="store_true",
        help="Generate and send digest immediately"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Generate digest but don't send email"
    )
    parser.add_argument(
        "--output", type=str, default=None,
        help="Save HTML output to file"
    )
    parser.add_argument(
        "--daemon", action="store_true",
        help="Run as daemon with scheduled execution"
    )

    args = parser.parse_args()

    if args.daemon:
        run_daemon(repo=args.repo)
    elif args.run_now or args.dry_run:
        generate_digest(dry_run=args.dry_run, output_file=args.output, repo=args.repo)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()

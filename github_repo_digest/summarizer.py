"""Generate AI summaries for PRs using Claude via AWS Bedrock."""

import os

import anthropic

from .github_client import get_pr_diff


def _get_client():
    """Create Anthropic client — uses Bedrock if configured, else direct API."""
    if os.environ.get("CLAUDE_CODE_USE_BEDROCK") == "1" or os.environ.get("AWS_BEARER_TOKEN_BEDROCK"):
        return anthropic.AnthropicBedrock(
            aws_region=os.environ.get("AWS_REGION", "us-east-2"),
        )
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    return anthropic.Anthropic(api_key=api_key)


def summarize_pr(pr):
    """Generate a concise AI description of what a PR does."""
    client = _get_client()

    title = pr.get("title", "")
    body = pr.get("body", "") or ""
    if len(body) > 3000:
        body = body[:3000] + "..."

    try:
        diff = get_pr_diff(pr["number"])
    except Exception:
        diff = "[diff unavailable]"

    prompt = f"""Summarize this GitHub PR in 1 sentence (max 25 words). State what changed and why. Be direct and technical.

Title: {title}

Description:
{body}

Diff (may be truncated):
{diff}

One sentence only, max 25 words."""

    model = "us.anthropic.claude-sonnet-4-20250514-v1:0" if os.environ.get("CLAUDE_CODE_USE_BEDROCK") else "claude-sonnet-4-6-20250514"

    response = client.messages.create(
        model=model,
        max_tokens=80,
        messages=[{"role": "user", "content": prompt}],
    )

    return response.content[0].text.strip()


def batch_summarize(prs):
    """Summarize a list of PRs, returning dict of pr_number -> summary."""
    summaries = {}
    for pr in prs:
        try:
            summaries[pr["number"]] = summarize_pr(pr)
        except Exception as e:
            summaries[pr["number"]] = f"Summary unavailable: {e}"
    return summaries

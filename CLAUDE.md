# GitHub Repo Digest Agent

## Overview

A generic weekly digest agent for any GitHub repository. Generates AI-powered PR summaries and sends them as styled HTML emails. Default repo: `sgl-project/sglang`.

## Architecture

- **github_client.py** — All GitHub API interactions. Every function accepts an optional `repo` parameter (defaults to config).
- **ranker.py** — Pre-filters by comment count, enriches top candidates, ranks by code size > impact > reviewers > comments
- **summarizer.py** — Generates 1-sentence AI summaries via Claude (supports direct API and AWS Bedrock)
- **emailer.py** — Sends HTML email via SMTP (falls back to sendmail)
- **main.py** — CLI entry point with `--repo` flag for targeting any repository
- **templates/digest.html** — Jinja2 HTML email template (repo name is dynamic)

## Key Design Decisions

- **Repo is configurable** — default `sgl-project/sglang` via `SGLANG_REPO` env var, overridable with `--repo owner/name`
- **Reporting window is Sunday-to-Sunday 00:00 UTC** — no overlap or gaps between reports
- **Pre-filtering** — Only enriches top N*2 PRs by comment count to reduce API calls
- **Organization inference** — Best-effort with disclaimer; tries org memberships → company field → commit email domain
- **AWS Bedrock support** — Auto-detects via `CLAUDE_CODE_USE_BEDROCK` env var

## Running

```bash
source .venv/bin/activate

# Default (sgl-project/sglang)
python -m github_repo_digest.main --dry-run --output preview.html

# Any other repo
python -m github_repo_digest.main --repo pytorch/pytorch --dry-run --output preview.html

# Send for real
python -m github_repo_digest.main --run-now

# Daemon mode
python -m github_repo_digest.main --daemon
```

## Configuration

All config via `config.env` or environment variables. Env vars take precedence.
The `--repo` CLI flag overrides the `SGLANG_REPO` config value at runtime.

## Dependencies

- anthropic (with bedrock extras for AWS)
- requests
- jinja2
- python-dotenv
- schedule

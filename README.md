# GitHub Repo Digest Agent

An AI-powered agent that generates a weekly summary of pull request activity for **any GitHub repository** and sends it as a styled HTML email. Default: [sgl-project/sglang](https://github.com/sgl-project/sglang).

## What It Does

1. **Computes a precise reporting window** (Sunday 00:00 UTC → Sunday 00:00 UTC) — no overlap or gaps between reports
2. **Fetches all merged PRs** in that window and **open PRs under active review**
3. **Ranks them** by code size → impact → number of reviewers → review comments
4. **Generates concise AI summaries** for each PR using Claude (Bedrock or direct API)
5. **Identifies the author's organization** from GitHub profiles and commit history
6. **Sends an HTML email** with:
   - Weekly overview (total PRs merged, reporting window)
   - Top 40 Merged PRs (ranked)
   - Top 40 PRs Under Review (ranked)

Subject format: `Sglang Summary Digest — Ww22` (repo name is dynamic)

## Quick Start

### Prerequisites

- Python 3.10+
- A [GitHub personal access token](https://github.com/settings/tokens) (read access to public repos)
- An [Anthropic API key](https://console.anthropic.com/) or AWS Bedrock access
- SMTP access (e.g., corporate mail server) or `sendmail`

### Installation

```bash
git clone https://github.com/yourname/github-repo-digest.git
cd github-repo-digest

# Create a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install
pip install -e .

# For AWS Bedrock support:
pip install -e ".[bedrock]"
```

### Configuration

```bash
cp config.env.example config.env
# Edit config.env with your tokens and email settings
```

Required fields in `config.env`:

| Variable | Description |
|----------|-------------|
| `GITHUB_TOKEN` | GitHub PAT with repo read access |
| `ANTHROPIC_API_KEY` | For direct Anthropic API (skip if using Bedrock) |
| `EMAIL_RECIPIENTS` | Comma-separated email addresses |
| `EMAIL_FROM` | Sender address |
| `SMTP_HOST` | SMTP server hostname (default: `smtp.intel.com`) |
| `SMTP_PORT` | SMTP port (default: `25`) |
| `SGLANG_REPO` | Default repo in `owner/name` format (default: `sgl-project/sglang`) |

For AWS Bedrock, set these environment variables instead of `ANTHROPIC_API_KEY`:
- `CLAUDE_CODE_USE_BEDROCK=1`
- `AWS_REGION` (default: `us-east-2`)
- `AWS_BEARER_TOKEN_BEDROCK` or standard AWS credentials

### Usage

```bash
# Generate and send for default repo (sgl-project/sglang)
repo-digest --run-now

# Target a different repo
repo-digest --repo pytorch/pytorch --run-now

# Dry run (no email sent, just print stats)
repo-digest --dry-run

# Save HTML to a file (for preview)
repo-digest --dry-run --output preview.html

# Target another repo with dry run
repo-digest --repo vllm-project/vllm --dry-run --output vllm_digest.html

# Run as a daemon (stays alive, sends every Monday 7AM IST)
repo-digest --daemon
```

### Cron Setup (Recommended)

```bash
# Auto-install a cron job for Monday 7AM IST (1:30 UTC)
./setup_cron.sh
```

Or manually:
```bash
crontab -e
# Add: 30 1 * * 1 cd /path/to/github-repo-digest && .venv/bin/python -m github_repo_digest.main --run-now
```

## Reporting Window

The agent uses a **Sunday-to-Sunday** window (00:00 UTC to 00:00 UTC). Each report covers exactly 7 days with no overlap between consecutive reports:

```
Report Ww22: Sun May 18 00:00 UTC → Sun May 25 00:00 UTC
Report Ww23: Sun May 25 00:00 UTC → Sun Jun 01 00:00 UTC
```

## How Ranking Works

PRs are ranked by these criteria (in priority order):

| Priority | Criterion | Measurement |
|----------|-----------|-------------|
| 1 | Code size | Lines added + deleted |
| 2 | Impact | Heuristic: files changed, keywords in title, labels |
| 3 | Reviewers | Unique reviewers on the PR |
| 4 | Review comments | Inline code review comments |

To reduce API calls, PRs are pre-filtered by comment count before expensive enrichment.

## Email Sections

### 1. Weekly Overview
- Total PRs merged in the reporting window
- Total PRs under active review
- Exact reporting window timestamps

### 2. Top 40 Merged PRs
Ranked table with: PR link, AI summary, author's organization*, diff stats

### 3. Top 40 PRs Under Review
Same format as merged PRs section

> *Organization names are inferred from GitHub profiles and commit history. They may not be accurate or up-to-date.

## Customization

| Setting | File | Description |
|---------|------|-------------|
| Target repo | CLI `--repo` or `config.env` → `SGLANG_REPO` | Any GitHub repo in `owner/name` format |
| Number of PRs | `config.env` → `TOP_N_PRS` | How many PRs per section (default: 40) |
| Schedule | `config.env` → `SCHEDULE_DAY`, `SCHEDULE_CRON` | Day and UTC time |
| SMTP server | `config.env` → `SMTP_HOST`, `SMTP_PORT` | Mail server settings |
| Email template | `github_repo_digest/templates/digest.html` | Full Jinja2 HTML template |
| Ranking logic | `github_repo_digest/ranker.py` | Adjust scoring weights |
| AI model | `github_repo_digest/summarizer.py` | Change Claude model |
| Summary length | `github_repo_digest/summarizer.py` | Adjust prompt and max_tokens |

## Project Structure

```
github-repo-digest/
├── pyproject.toml              # Package metadata and dependencies
├── config.env.example          # Configuration template
├── setup_cron.sh               # Cron installation helper
├── README.md
├── CLAUDE.md                   # Agent skill definition
└── github_repo_digest/
    ├── __init__.py
    ├── main.py                 # Entry point, CLI (--repo flag), scheduler
    ├── config.py               # Load environment config
    ├── github_client.py        # GitHub API interactions (repo-parameterized)
    ├── ranker.py               # PR ranking logic
    ├── summarizer.py           # Claude AI summarization
    ├── emailer.py              # SMTP/sendmail integration
    └── templates/
        └── digest.html         # Jinja2 HTML email template (dynamic repo name)
```

## License

MIT

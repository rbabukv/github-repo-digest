#!/bin/bash
# Install a system cron job to run the digest every Monday at 01:30 UTC (07:00 IST)

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON=$(which python3)
CRON_CMD="30 1 * * 1 cd $SCRIPT_DIR && $PYTHON -m github_repo_digest.main --run-now >> /var/log/repo-digest.log 2>&1"

# Check if cron job already exists
if crontab -l 2>/dev/null | grep -q "github_repo_digest"; then
    echo "Cron job already exists. Updating..."
    crontab -l | grep -v "github_repo_digest" | crontab -
fi

# Remove old sglang_weekly_digest cron if present
if crontab -l 2>/dev/null | grep -q "sglang_weekly_digest"; then
    crontab -l | grep -v "sglang_weekly_digest" | crontab -
fi

# Add the cron job
(crontab -l 2>/dev/null; echo "$CRON_CMD") | crontab -

echo "✅ Cron job installed:"
echo "   Schedule: Every Monday at 01:30 UTC (07:00 IST)"
echo "   Command: $CRON_CMD"
echo ""
echo "Verify with: crontab -l"

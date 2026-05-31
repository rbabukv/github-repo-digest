import os
from pathlib import Path

from dotenv import load_dotenv

_env_path = Path(__file__).resolve().parent.parent / "config.env"
if _env_path.exists():
    load_dotenv(_env_path)


GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
EMAIL_RECIPIENTS = [e.strip() for e in os.environ.get("EMAIL_RECIPIENTS", "").split(",") if e.strip()]
EMAIL_FROM = os.environ.get("EMAIL_FROM", "No Reply <repo-digest@intel.com>")
SGLANG_REPO = os.environ.get("SGLANG_REPO", "sgl-project/sglang")
TOP_N_PRS = int(os.environ.get("TOP_N_PRS", "40"))
SCHEDULE_CRON = os.environ.get("SCHEDULE_CRON", "01:30")
SCHEDULE_DAY = os.environ.get("SCHEDULE_DAY", "monday")

"""Shared pytest fixtures for Cloudability MCP server tests."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent

# Load at import time so collection-time skip marks see credentials from `.env`.
load_dotenv(REPO_ROOT / ".env")


def live_cloudability_credentials_configured() -> bool:
    """Return True when credentials for a live API call are available."""
    return bool(
        os.getenv("CLOUDABILITY_KEY_ACCESS")
        and os.getenv("CLOUDABILITY_KEY_SECRET")
        and os.getenv("CLOUDABILITY_ENVIRONMENT_ID")
    )


requires_live_cloudability = pytest.mark.skipif(
    not live_cloudability_credentials_configured(),
    reason=(
        "Live Cloudability credentials not configured. "
        "Copy .env.example to .env and set CLOUDABILITY_KEY_ACCESS, "
        "CLOUDABILITY_KEY_SECRET, and CLOUDABILITY_ENVIRONMENT_ID "
        "."
    ),
)

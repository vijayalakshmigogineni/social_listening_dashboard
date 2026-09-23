"""
Thin, shared Apify REST client (raw HTTP, no apify_client SDK dependency --
matches the pattern already proven in testing/reddit/test_normalise_reddit.py
and testing/problem-intelligence/reddit/apify_field_validation.py).
"""

from __future__ import annotations

import time
from typing import Any

import requests

from app.config import APIFY_TOKEN

TERMINAL_STATUSES = {"SUCCEEDED", "FAILED", "ABORTED", "TIMED-OUT"}


class ApifyRunError(RuntimeError):
    pass


def run_actor_sync(
    actor_id: str,
    run_input: dict[str, Any],
    token: str | None = None,
    poll_interval_s: float = 5.0,
    timeout_s: float = 600.0,
) -> list[dict[str, Any]]:
    """Start an Apify actor run, block until it finishes, return dataset items."""

    token = token or APIFY_TOKEN
    if not token:
        raise ApifyRunError("No Apify token configured (APIFY_TOKEN in .env)")

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    normalized_actor_id = actor_id.replace("/", "~")

    start_resp = requests.post(
        f"https://api.apify.com/v2/acts/{normalized_actor_id}/runs",
        headers=headers,
        json=run_input,
        timeout=60,
    )
    if start_resp.status_code != 201:
        raise ApifyRunError(f"Failed to start actor {normalized_actor_id}: {start_resp.text}")

    run_data = start_resp.json()["data"]
    run_id = run_data["id"]
    dataset_id = run_data["defaultDatasetId"]

    status_url = f"https://api.apify.com/v2/actor-runs/{run_id}"
    elapsed = 0.0
    status = "READY"

    while elapsed < timeout_s:
        status_resp = requests.get(status_url, params={"token": token}, timeout=30)
        if status_resp.status_code != 200:
            raise ApifyRunError(f"Could not check run status: {status_resp.text}")

        status = status_resp.json()["data"]["status"]
        if status in TERMINAL_STATUSES:
            break

        time.sleep(poll_interval_s)
        elapsed += poll_interval_s

    if status != "SUCCEEDED":
        raise ApifyRunError(f"Actor run {run_id} ended with status={status}")

    dataset_resp = requests.get(
        f"https://api.apify.com/v2/datasets/{dataset_id}/items",
        params={"token": token, "clean": "true"},
        timeout=60,
    )
    if dataset_resp.status_code != 200:
        raise ApifyRunError(f"Could not retrieve dataset {dataset_id}: {dataset_resp.text}")

    return dataset_resp.json()

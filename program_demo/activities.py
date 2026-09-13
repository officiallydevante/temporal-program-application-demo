"""All activities: the simulated (and one real) side-effecting work the workflow orchestrates.

Kept deliberately simple and demo-friendly:
- validate_application: trivial guard clause, first link in the chain.
- screen_applicant: the heartbeat / crash-recovery headline activity.
- add_to_roster: the automatic-retry demo activity; writes to data/roster.json.
- send_acceptance_email / send_withdrawal_email: real sends via Resend's HTTP API.
"""

import asyncio
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import httpx
from temporalio import activity
from temporalio.exceptions import ApplicationError

from program_demo.email_templates import render_acceptance_email, render_withdrawal_email
from program_demo.shared import ApplicationInput, RosterEntry, SCREENING_STEPS

ROSTER_PATH = Path(__file__).parent.parent / "data" / "roster.json"

RESEND_API = "https://api.resend.com/emails"
DEFAULT_FROM = "Studio 22 Productions <devante@studio22productions.co>"


@activity.defn
async def validate_application(app: ApplicationInput) -> None:
    activity.logger.info(f"Validating application {app.application_id} ({app.name})")
    await asyncio.sleep(1)
    if not app.name.strip() or not app.email.strip():
        raise ApplicationError("Name and email are required", non_retryable=True)


@activity.defn
async def screen_applicant(app: ApplicationInput) -> None:
    """Simulates automated screening checks. Heartbeats after each step so a
    killed-and-restarted worker resumes from the last completed step instead
    of starting the loop over — this is the demo's headline feature."""
    info = activity.info()
    start_step = 0
    if info.heartbeat_details:
        start_step = info.heartbeat_details[0]
        activity.logger.info(
            f"Resuming screening from check {start_step}/{SCREENING_STEPS} (heartbeat detail found)"
        )
    for step in range(start_step, SCREENING_STEPS):
        activity.logger.info(f"Screening check {step + 1}/{SCREENING_STEPS} for {app.application_id}")
        await asyncio.sleep(3)
        activity.heartbeat(step + 1)
    activity.logger.info(f"Screening complete for {app.application_id}")


@activity.defn
async def add_to_roster(app: ApplicationInput) -> RosterEntry:
    """Fails on attempts 1-2 (simulated roster-file lock contention), succeeds on
    attempt 3 — deterministic via the SDK's own per-execution attempt counter, so
    this repeats identically every demo run with no mocking or randomness."""
    attempt = activity.info().attempt
    activity.logger.info(f"add_to_roster attempt {attempt} for {app.application_id}")
    await asyncio.sleep(1)
    if attempt < 3:
        raise ApplicationError(f"Simulated roster-file lock contention (attempt {attempt})")

    entry = RosterEntry(
        application_id=app.application_id,
        name=app.name,
        email=app.email,
        track=app.track,
        accepted_at=datetime.now(timezone.utc).isoformat(),
    )
    _append_roster_entry(entry)
    return entry


def _append_roster_entry(entry: RosterEntry) -> None:
    ROSTER_PATH.parent.mkdir(parents=True, exist_ok=True)
    roster = []
    if ROSTER_PATH.exists():
        try:
            roster = json.loads(ROSTER_PATH.read_text())
        except json.JSONDecodeError:
            roster = []
    if any(r.get("application_id") == entry.application_id for r in roster):
        return  # already recorded — keeps this idempotent if ever retried again
    roster.append(entry.__dict__)
    ROSTER_PATH.write_text(json.dumps(roster, indent=2) + "\n")


@activity.defn
async def send_acceptance_email(app: ApplicationInput) -> None:
    html = render_acceptance_email(app.name, app.track)
    await _send_email(to=app.email, subject="You're accepted!", html=html)


@activity.defn
async def send_withdrawal_email(app: ApplicationInput) -> None:
    html = render_withdrawal_email(app.name)
    await _send_email(to=app.email, subject="Application withdrawn", html=html)


async def _send_email(to: str, subject: str, html: str) -> None:
    api_key = os.environ.get("RESEND_API_KEY")
    if not api_key:
        raise ApplicationError("RESEND_API_KEY is not set", non_retryable=True)
    from_address = os.environ.get("RESEND_FROM_ADDRESS", DEFAULT_FROM)

    async with httpx.AsyncClient() as client:
        response = await client.post(
            RESEND_API,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"from": from_address, "to": [to], "subject": subject, "html": html},
            timeout=15,
        )
    if response.status_code >= 400:
        raise ApplicationError(f"Resend send failed: {response.status_code} {response.text}")
    activity.logger.info(f"Email sent to {to}: {subject}")

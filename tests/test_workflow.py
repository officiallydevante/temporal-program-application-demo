"""Workflow-level tests using Temporal's time-skipping test environment.

Crash-recovery (killing and restarting a worker mid-`screen_applicant` to prove
heartbeat-based resume) is intentionally NOT covered here — it requires a real
killed-and-restarted worker process. See the README's walkthrough script for
that demo instead; these tests cover the parts that are meaningfully unit-testable.
"""

import json
import logging
import uuid

import pytest
from temporalio import activity
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from program_demo import activities
from program_demo.shared import ApplicationInput, RosterEntry, TASK_QUEUE
from program_demo.workflow import ProgramApplicationWorkflow


@activity.defn(name="screen_applicant")
async def fast_screen_applicant(app: ApplicationInput) -> None:
    """Stand-in for the real ~15s heartbeat loop — that behavior isn't under
    test at the workflow level, so this just returns immediately."""


def make_application() -> ApplicationInput:
    return ApplicationInput(
        application_id=f"application-{uuid.uuid4()}",
        name="Jordan Lee",
        email="jordan@example.com",
        track="Video Editing",
        motivation="Want to learn the craft.",
    )


def make_spy_email_activities():
    calls = {"accepted": [], "withdrawn": []}

    @activity.defn(name="send_acceptance_email")
    async def send_acceptance_email(app: ApplicationInput) -> None:
        calls["accepted"].append(app.application_id)

    @activity.defn(name="send_withdrawal_email")
    async def send_withdrawal_email(app: ApplicationInput) -> None:
        calls["withdrawn"].append(app.application_id)

    return calls, send_acceptance_email, send_withdrawal_email


@pytest.mark.asyncio
async def test_happy_path_completes(monkeypatch, tmp_path):
    monkeypatch.setattr(activities, "ROSTER_PATH", tmp_path / "roster.json")
    calls, send_acceptance_email, send_withdrawal_email = make_spy_email_activities()
    application = make_application()

    async with await WorkflowEnvironment.start_time_skipping() as env:
        async with Worker(
            env.client,
            task_queue=TASK_QUEUE,
            workflows=[ProgramApplicationWorkflow],
            activities=[
                activities.validate_application,
                fast_screen_applicant,
                activities.add_to_roster,
                send_acceptance_email,
                send_withdrawal_email,
            ],
        ):
            result = await env.client.execute_workflow(
                ProgramApplicationWorkflow.run,
                application,
                id=application.application_id,
                task_queue=TASK_QUEUE,
            )

    assert result.status == "accepted"
    assert calls["accepted"] == [application.application_id]
    assert calls["withdrawn"] == []
    roster = json.loads((tmp_path / "roster.json").read_text())
    assert roster[0]["application_id"] == application.application_id


@pytest.mark.asyncio
async def test_add_to_roster_retries_then_succeeds(monkeypatch, tmp_path, caplog):
    """Exercises the real add_to_roster (not a spy) so its attempt-based failure
    logic actually runs. Proves the retry happened by counting its own attempt
    log lines — history-event introspection turned out not to reliably surface
    per-attempt Started/Failed events against the time-skipping test server, so
    this is the more robust signal."""
    monkeypatch.setattr(activities, "ROSTER_PATH", tmp_path / "roster.json")
    calls, send_acceptance_email, send_withdrawal_email = make_spy_email_activities()
    application = make_application()

    caplog.set_level(logging.INFO)
    async with await WorkflowEnvironment.start_time_skipping() as env:
        async with Worker(
            env.client,
            task_queue=TASK_QUEUE,
            workflows=[ProgramApplicationWorkflow],
            activities=[
                activities.validate_application,
                fast_screen_applicant,
                activities.add_to_roster,
                send_acceptance_email,
                send_withdrawal_email,
            ],
        ):
            result = await env.client.execute_workflow(
                ProgramApplicationWorkflow.run,
                application,
                id=application.application_id,
                task_queue=TASK_QUEUE,
            )

    # activity.logger appends a context dict to each message, so match by prefix.
    attempt_lines = [
        r.getMessage()
        for r in caplog.records
        if "add_to_roster attempt" in r.getMessage() and application.application_id in r.getMessage()
    ]
    expected_prefixes = [
        f"add_to_roster attempt {n} for {application.application_id}" for n in (1, 2, 3)
    ]
    assert len(attempt_lines) == 3
    assert all(line.startswith(prefix) for line, prefix in zip(attempt_lines, expected_prefixes))
    assert result.status == "accepted"


@pytest.mark.asyncio
async def test_withdraw_signal_skips_roster_and_sends_withdrawal_email(monkeypatch, tmp_path):
    monkeypatch.setattr(activities, "ROSTER_PATH", tmp_path / "roster.json")
    calls, send_acceptance_email, send_withdrawal_email = make_spy_email_activities()
    application = make_application()
    roster_calls = []

    @activity.defn(name="add_to_roster")
    async def spy_add_to_roster(app: ApplicationInput) -> RosterEntry:
        roster_calls.append(app.application_id)
        return RosterEntry(app.application_id, app.name, app.email, app.track, "unused")

    async with await WorkflowEnvironment.start_time_skipping() as env:
        async with Worker(
            env.client,
            task_queue=TASK_QUEUE,
            workflows=[ProgramApplicationWorkflow],
            activities=[
                activities.validate_application,
                fast_screen_applicant,
                spy_add_to_roster,
                send_acceptance_email,
                send_withdrawal_email,
            ],
        ):
            handle = await env.client.start_workflow(
                ProgramApplicationWorkflow.run,
                application,
                id=application.application_id,
                task_queue=TASK_QUEUE,
            )
            await handle.signal(ProgramApplicationWorkflow.withdraw_application)
            result = await handle.result()

    assert result.status == "withdrawn"
    assert roster_calls == []
    assert calls["withdrawn"] == [application.application_id]
    assert calls["accepted"] == []

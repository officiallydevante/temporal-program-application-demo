# Temporal Program-Application Demo

A live walkthrough of Temporal orchestration: fill out a small web form, and a
Temporal workflow validates the application, runs automated screening, adds
the applicant to a roster file in this repo, and emails them a real
acceptance notice via Resend.

## What this demonstrates

- **Multi-activity orchestration** — a real sequence of steps, written as plain
  Python orchestration code (`program_demo/workflow.py`), not hidden behind a
  framework.
- **Automatic retries** — `add_to_roster` fails on its first two attempts and
  succeeds on the third, deterministically, every run — visible live in the
  Temporal Web UI's event history.
- **Heartbeating + crash recovery** — the headline feature. `screen_applicant`
  heartbeats its progress; kill the worker mid-run and restart it, and it
  resumes from the last completed step instead of starting over.
- **Signals** — a real "Withdraw my application" button on the status page
  sends a signal into the running workflow, which takes a different path
  (a withdrawal email instead of acceptance, no roster entry written).
- **A query** powers the status page's live-updating view, with zero effect on
  workflow execution.
- **Real email**, sent through the same Resend integration pattern used in
  `studio22-productions` — this isn't a toy, it actually emails whoever fills
  out the form.

## Prerequisites

- [Homebrew](https://brew.sh) (macOS)
- Python 3.9+ (`python3 --version`)
- A Resend API key (same account/domain as `studio22-productions`)

## Setup

```bash
# 1. Temporal CLI (dev server + Web UI)
brew install temporal
temporal --version

# 2. Python environment
python3 -m venv .venv
source .venv/bin/activate
pip install -e .

# 3. Email config
cp .env.example .env
# then fill in RESEND_API_KEY in .env
```

## Project layout

```
program_demo/
├── shared.py             # TASK_QUEUE + ApplicationInput/RosterEntry/ApplicationResult
├── activities.py         # validate_application, screen_applicant, add_to_roster, send_*_email
├── email_templates.py    # HTML templates (mirrors studio22-productions' Resend style)
├── workflow.py           # ProgramApplicationWorkflow — orchestration only
├── worker.py             # python -m program_demo.worker
└── web.py                # FastAPI app — the form + status page

data/roster.json          # git-tracked; add_to_roster appends accepted applicants here
tests/test_workflow.py    # time-skipping tests for the parts that unit-test cleanly
```

## Running it

Three terminals, left running for the whole session:

```bash
# Terminal 1 — Temporal dev server + Web UI (localhost:8233)
temporal server start-dev

# Terminal 2 — the worker
source .venv/bin/activate
python -m program_demo.worker

# Terminal 3 — the web app
source .venv/bin/activate
uvicorn program_demo.web:app --reload
# open http://localhost:8000
```

## Walkthrough script

Run through in order. Keep the Temporal Web UI (`http://localhost:8233`) open
on a second window throughout.

1. **Start everything** — dev server, worker, web app. Briefly show
   `worker.py`'s registration call and explain task queues: the worker polls
   one queue for both workflow and activity tasks.

2. **Run #1 — happy path.** Submit the form. Follow the redirect to the status
   page, then switch to the Web UI and open this workflow's Event History.
   Walk through each activity's `Scheduled → Started → Completed` triple —
   this is multi-activity orchestration made visible.

3. **Point out the retries**, still in run #1's history: `add_to_roster` shows
   two `ActivityTaskFailed` events before `ActivityTaskCompleted`. Explain the
   `RetryPolicy` fields on that `execute_activity` call in `workflow.py` against
   what just happened.

4. **Run #2 — crash recovery (the headline moment).** Submit a second
   application. Watch Terminal 2's logs move through `validate_application`
   into `screen_applicant`'s `"Screening check X/5"` lines.
   - After ~2 of 5 checks print, hard-kill the worker:
     `ps aux | grep program_demo.worker` → `kill -9 <pid>` (a hard kill, not
     Ctrl+C — there's no graceful shutdown involved).
   - In the Web UI's Pending Activities panel, show the heartbeat detail frozen
     at the last reported step. Once the 5s heartbeat timeout elapses, point
     out the `ActivityTaskTimedOut` event followed by a new
     `ActivityTaskScheduled`.
   - Restart the worker with the identical command. Watch it log
     `"Resuming screening from check 3/5 (heartbeat detail found)"` and finish
     the remaining checks — it did not start over. The status page picks this
     up automatically via its poll loop.

5. **Run #3 — signal / withdrawal.** Submit a third application. While
   `screen_applicant` is still running (or right after submitting), click
   **Withdraw my application** on the status page. In the Web UI, show the
   `WorkflowExecutionSignaled` event, then the workflow skipping straight to
   `send_withdrawal_email` — no `add_to_roster` call at all. Check
   `data/roster.json` to confirm this applicant was never added.

6. **Run the tests.** `pytest` — walk through the three tests, emphasizing
   they complete in seconds despite modeling multi-step, retrying,
   signal-driven workflows. That's the payoff of Temporal's time-skipping test
   environment.

```bash
pytest
```

## Where to go next

Not built here, but worth mentioning as next steps:

- **Child workflows** — e.g. breaking `screen_applicant` into a child workflow
  per check.
- **Sagas** — a formalized compensation framework, vs. this demo's hand-rolled
  single withdrawal branch.
- **Schedules** — cron-style recurring workflow starts.
- **Versioning / patching** — safely evolving a running workflow's code.
- **Search attributes** — querying/filtering workflows by business fields
  directly in the Web UI.

"""Shared constants and data types used across the workflow, activities, worker, and web app."""

from dataclasses import dataclass

TASK_QUEUE = "program-application-task-queue"

# Screening loop length, shared between the activity (which heartbeats each
# step) and anything that needs to talk about "step X of N" consistently.
SCREENING_STEPS = 5


@dataclass
class ApplicationInput:
    application_id: str
    name: str
    email: str
    track: str
    motivation: str


@dataclass
class RosterEntry:
    application_id: str
    name: str
    email: str
    track: str
    accepted_at: str  # ISO timestamp


@dataclass
class ApplicationResult:
    application_id: str
    status: str  # "accepted" | "withdrawn"
    detail: str

"""ProgramApplicationWorkflow — pure orchestration. No I/O happens here directly;
every side effect (screening, roster writes, emails) lives in activities.py."""

from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from program_demo import activities
    from program_demo.shared import ApplicationInput, ApplicationResult

DEFAULT_RETRY = RetryPolicy(maximum_attempts=3)
FLAKY_RETRY = RetryPolicy(
    initial_interval=timedelta(seconds=1),
    backoff_coefficient=2.0,
    maximum_interval=timedelta(seconds=10),
    maximum_attempts=5,
)


@workflow.defn
class ProgramApplicationWorkflow:
    def __init__(self) -> None:
        self._status: str = "started"
        self._withdrawn: bool = False

    @workflow.signal
    async def withdraw_application(self) -> None:
        self._withdrawn = True

    @workflow.query
    def get_status(self) -> str:
        return self._status

    @workflow.run
    async def run(self, app: ApplicationInput) -> ApplicationResult:
        self._status = "validating"
        await workflow.execute_activity(
            activities.validate_application,
            app,
            start_to_close_timeout=timedelta(seconds=10),
            retry_policy=DEFAULT_RETRY,
        )

        self._status = "screening"
        await workflow.execute_activity(
            activities.screen_applicant,
            app,
            start_to_close_timeout=timedelta(minutes=2),
            heartbeat_timeout=timedelta(seconds=5),
            retry_policy=FLAKY_RETRY,
        )
        if self._withdrawn:
            return await self._withdraw(app)

        self._status = "adding_to_roster"
        await workflow.execute_activity(
            activities.add_to_roster,
            app,
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=FLAKY_RETRY,
        )
        if self._withdrawn:
            return await self._withdraw(app)

        self._status = "emailing_acceptance"
        await workflow.execute_activity(
            activities.send_acceptance_email,
            app,
            start_to_close_timeout=timedelta(seconds=15),
            retry_policy=DEFAULT_RETRY,
        )

        self._status = "accepted"
        return ApplicationResult(app.application_id, "accepted", "Application accepted.")

    async def _withdraw(self, app: ApplicationInput) -> ApplicationResult:
        self._status = "emailing_withdrawal"
        await workflow.execute_activity(
            activities.send_withdrawal_email,
            app,
            start_to_close_timeout=timedelta(seconds=15),
            retry_policy=DEFAULT_RETRY,
        )
        self._status = "withdrawn"
        return ApplicationResult(app.application_id, "withdrawn", "Application withdrawn before acceptance.")

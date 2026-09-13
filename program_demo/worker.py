"""Run with: python -m program_demo.worker

Connects to the local Temporal dev server and polls TASK_QUEUE for both
workflow and activity tasks. Restarting this process mid-`screen_applicant`
is the crash-recovery demo — see the README's walkthrough script.
"""

import asyncio
import logging

from dotenv import load_dotenv
from temporalio.client import Client
from temporalio.worker import Worker

from program_demo import activities
from program_demo.shared import TASK_QUEUE
from program_demo.workflow import ProgramApplicationWorkflow

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


async def main() -> None:
    load_dotenv()
    client = await Client.connect("localhost:7233")
    worker = Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=[ProgramApplicationWorkflow],
        activities=[
            activities.validate_application,
            activities.screen_applicant,
            activities.add_to_roster,
            activities.send_acceptance_email,
            activities.send_withdrawal_email,
        ],
    )
    logging.info(f"Worker started, polling task queue '{TASK_QUEUE}'")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())

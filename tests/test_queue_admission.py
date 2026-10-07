import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from fastapi import HTTPException
from unittest.mock import patch

from backend.api import routes
from backend.models.schemas import AnalysisStatusEnum, AnalysisStatusResponse


class TestQueueAdmission(unittest.TestCase):
    def test_executor_shutdown_drains_admitted_jobs(self):
        class RecordingExecutor:
            def __init__(self):
                self.options = None

            def shutdown(self, **kwargs):
                self.options = kwargs

        executor = RecordingExecutor()
        with patch.object(routes, "ANALYSIS_EXECUTOR", executor):
            routes.shutdown_analysis_executor()
        self.assertEqual(executor.options, {"wait": True, "cancel_futures": False})

    def test_concurrent_reservations_never_exceed_limit(self):
        reserved_ids = []
        original_tasks = dict(routes.ACTIVE_TASKS)
        try:
            routes.ACTIVE_TASKS.clear()
            for index in range(routes.MAX_PENDING_JOBS - 1):
                task_id = f"preexisting-{index}"
                routes.ACTIVE_TASKS[task_id] = AnalysisStatusResponse(
                    analysis_id=task_id,
                    status=AnalysisStatusEnum.QUEUED,
                    current_stage="QUEUED",
                    message="already reserved",
                )

            start = threading.Barrier(3)

            def reserve():
                start.wait()
                try:
                    return routes.reserve_analysis_slot()
                except HTTPException as exc:
                    return exc.status_code

            with ThreadPoolExecutor(max_workers=2) as callers:
                futures = [callers.submit(reserve) for _ in range(2)]
                start.wait()
                results = [future.result() for future in futures]

            reserved_ids = [value for value in results if isinstance(value, str)]
            rejections = [value for value in results if isinstance(value, int)]
            self.assertEqual(len(reserved_ids), 1)
            self.assertEqual(rejections, [429])
            self.assertEqual(
                sum(
                    task.status not in (AnalysisStatusEnum.COMPLETED, AnalysisStatusEnum.FAILED)
                    for task in routes.ACTIVE_TASKS.values()
                ),
                routes.MAX_PENDING_JOBS,
            )
        finally:
            routes.ACTIVE_TASKS.clear()
            routes.ACTIVE_TASKS.update(original_tasks)


if __name__ == "__main__":
    unittest.main()

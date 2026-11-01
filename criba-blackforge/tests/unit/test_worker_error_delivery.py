"""A failed operation must reach the UI even when it raises RuntimeError."""

import pytest
from criba.ui.actions import Worker


@pytest.mark.parametrize("kind", [RuntimeError, ValueError])
def test_worker_emits_operation_failure(kind):
    failures = []
    completed = []

    def operation():
        raise kind("synthetic operation failure")

    worker = Worker(operation)
    worker.signals.fail.connect(failures.append)
    worker.signals.done.connect(completed.append)
    worker.run()
    assert len(failures) == 1
    assert "synthetic operation failure" in failures[0]
    assert not completed


def test_worker_ignores_a_destroyed_signal_source_after_operation_completes():
    from shiboken6 import delete

    worker = Worker(lambda: "completed after window closed")
    delete(worker.signals)
    worker.run()

"""Background job queue — daemon-thread worker over ``queue.Queue``.

Shape borrowed from v13's ``jobs/async_queue.py`` + ``worker_loop.py``.
Domain-free: the queue accepts any ``Callable[[], Any]`` and routes the
result (or exception) to the supplied callback.

Why this lives here, not in biocore: per the freeze rule on biocore
(see ``V13_REUSE_MAP.md``), domain-neutral helpers are copy-forked
into siblings rather than centrally extracted. If three or more
siblings end up implementing this same shape, that becomes a real
extraction signal — but not yet.

Worker semantics:

- Single daemon worker thread per ``BackgroundWorkerLoop``. Submit
  multiple jobs and they run sequentially in submission order.
- Daemon thread → process exit does not block on pending jobs.
- Exceptions in the job body are caught and routed to ``on_error``;
  they do not kill the worker thread.
- ``status()`` returns a snapshot dict — useful in dashboards and
  tests but does not synchronise the queue.
"""

from __future__ import annotations

import queue
import threading
from typing import Any, Callable

JobFn = Callable[[], Any]
SuccessCb = Callable[[Any], None]
ErrorCb = Callable[[BaseException], None]


class BackgroundWorkerLoop:
    """Single-thread daemon worker draining a FIFO queue."""

    def __init__(self, name: str = "rescue-worker-loop") -> None:
        self._q: "queue.Queue[tuple[str, JobFn, SuccessCb, ErrorCb] | None]" = (
            queue.Queue()
        )
        self._name = name
        self._thread = threading.Thread(
            target=self._run, daemon=True, name=name
        )
        self._started = False
        self._lock = threading.Lock()

    def start(self) -> None:
        with self._lock:
            if not self._started:
                self._thread.start()
                self._started = True

    def submit(
        self,
        job_id: str,
        fn: JobFn,
        on_success: SuccessCb,
        on_error: ErrorCb,
    ) -> None:
        if not job_id:
            raise ValueError("job_id must not be empty")
        self.start()
        self._q.put((job_id, fn, on_success, on_error))

    def status(self) -> dict[str, Any]:
        return {
            "name": self._name,
            "started": self._started,
            "alive": self._thread.is_alive() if self._started else False,
            "queue_depth": self._q.qsize(),
        }

    def join(self) -> None:
        """Block until every submitted job has been picked up + run.

        Tests use this; production code generally does not.
        """
        self._q.join()

    def _run(self) -> None:
        while True:
            item = self._q.get()
            if item is None:
                self._q.task_done()
                return
            _job_id, fn, on_success, on_error = item
            try:
                result = fn()
                on_success(result)
            except BaseException as exc:  # noqa: BLE001
                on_error(exc)
            finally:
                self._q.task_done()


class AsyncJobQueue:
    """Thin façade over ``BackgroundWorkerLoop``.

    Kept as a separate class so a future deployment can swap in a
    different worker implementation (e.g. multiprocessing pool, redis
    queue) without changing call-sites.
    """

    def __init__(self) -> None:
        self._worker = BackgroundWorkerLoop()

    def submit(
        self,
        job_id: str,
        fn: JobFn,
        on_success: SuccessCb,
        on_error: ErrorCb,
    ) -> None:
        self._worker.submit(job_id, fn, on_success, on_error)

    def status(self) -> dict[str, Any]:
        return self._worker.status()

    def join(self) -> None:
        self._worker.join()

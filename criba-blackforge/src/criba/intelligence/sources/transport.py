"""IIE HTTP transport (P03): retries, timeouts, rate-limit responses, budget.

No adapter imports httpx directly; everything goes through Transport so tests
inject a fake sender (§101 no-network CI). Real sender is lazy-imported.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Response:
    status: int
    text: str
    headers: dict[str, str] = field(default_factory=dict)

    def json(self) -> Any:
        import json

        return json.loads(self.text)


@dataclass
class TransportBudget:
    """Blueprint §35: per-run request accounting."""

    max_requests: int = 20
    max_runtime_s: float = 120.0
    requests_made: int = 0
    started_at: float = field(default_factory=time.monotonic)
    _lock: Any = field(default_factory=threading.Lock, init=False, repr=False, compare=False)

    def spend(self) -> bool:
        """True if a request may proceed; False if budget exhausted."""
        with self._lock:
            if self.requests_made >= self.max_requests or self.remaining_s <= 0:
                return False
            self.requests_made += 1
            return True

    @property
    def remaining_s(self) -> float:
        return max(0.0, self.max_runtime_s - (time.monotonic() - self.started_at))

    @property
    def exhausted(self) -> bool:
        with self._lock:
            return self.requests_made >= self.max_requests or self.remaining_s <= 0


class BudgetExceeded(Exception):
    pass


class OfflineBlocked(Exception):
    """Raised when a request is attempted while offline mode is active.

    The offline gate lives here — at the shared transport every source must
    cross — so no acquisition path can leak a network request (mandate §6).
    """


class AcquisitionCancelled(Exception):
    """Cancellation stops new requests/retries; an in-flight GET may finish."""


class Transport:
    """GET sender with retry/backoff/429 handling. sender is injectable."""

    RETRY_STATUSES = {0, 429, 500, 502, 503, 504}

    def __init__(
        self,
        sender: Callable[..., Response] | None = None,
        budget: TransportBudget | None = None,
        max_retries: int = 2,
        timeout_s: float = 20.0,
        user_agent: str = "criba-iie/0.1 (+research)",
        offline: bool = False,
        cancel_event: threading.Event | None = None,
    ):
        self._sender = sender
        self.budget = budget or TransportBudget()
        self.max_retries = max_retries
        self.timeout_s = timeout_s
        self.user_agent = user_agent
        self.offline = offline
        self.cancel_event = cancel_event
        self._thread_metrics = threading.local()

    @property
    def thread_request_count(self) -> int:
        """Actual sender attempts on this thread, including failed retries."""
        return int(getattr(self._thread_metrics, "requests", 0))

    def _real_sender(
        self,
        url: str,
        params: dict[str, Any] | None,
        timeout: float,
        headers: dict[str, Any] | None,
    ) -> Response:
        import httpx  # lazy: only hit when actually going online

        h = {"User-Agent": self.user_agent}
        if headers:
            h.update(headers)
        with httpx.Client(timeout=timeout) as client:
            r = client.get(url, params=params, headers=h)
            return Response(status=r.status_code, text=r.text, headers=dict(r.headers))

    def get(
        self, url: str, params: dict[str, Any] | None = None, headers: dict[str, Any] | None = None
    ) -> Response:
        """Single GET honoring offline gate + budget + retries. Raises BudgetExceeded."""
        if self.offline:
            raise OfflineBlocked(f"offline: request to {url} blocked at transport")
        last: Response | None = None
        for attempt in range(self.max_retries + 1):
            if self.cancel_event is not None and self.cancel_event.is_set():
                raise AcquisitionCancelled("acquisition cancelled before next HTTP request")
            if not self.budget.spend():
                raise BudgetExceeded(
                    f"budget exhausted ({self.budget.requests_made}/"
                    f"{self.budget.max_requests} requests)"
                )
            sender = self._sender or self._real_sender
            self._thread_metrics.requests = self.thread_request_count + 1
            try:
                resp = sender(
                    url,
                    params=params,
                    timeout=min(self.timeout_s, self.budget.remaining_s),
                    headers=headers,
                )
            except Exception as exc:  # network error -> retryable
                last = Response(status=0, text=f"network error: {exc}")
                resp = last
            if resp.status == 200:
                return resp
            if resp.status in self.RETRY_STATUSES and attempt < self.max_retries:
                delay = min(float(2**attempt), 4.0)
                if resp.status == 429:
                    try:
                        retry_after = float(
                            resp.headers.get("retry-after", resp.headers.get("Retry-After", "0"))
                        )
                        # A long server cooldown ends this bounded refresh;
                        # retrying earlier would violate the upstream delay.
                        if retry_after > min(60.0, self.budget.remaining_s):
                            return resp
                        delay = max(delay, retry_after)
                    except ValueError:
                        pass
                delay = min(delay, 60.0, self.budget.remaining_s)
                if self.cancel_event is None:
                    time.sleep(delay)
                elif self.cancel_event.wait(delay):
                    raise AcquisitionCancelled("acquisition cancelled during retry backoff")
                continue
            return resp
        return last or Response(status=0, text="unreachable")

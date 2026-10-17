# RetryBox pilot task

Repair `JobStore.run()` without changing its public signature.

Required observable behavior:

1. The first `run(job_id, payload, handler)` executes the handler and persists
   the result.
2. Repeating the same `job_id` with semantically identical JSON payload returns
   the persisted result and does **not** execute the handler again.
3. Reusing the same `job_id` with different payload content must fail explicitly;
   it must never return the old result as if it belonged to the new payload.
4. Two different job IDs with identical payloads are independent jobs.
5. The behavior must survive constructing a new `JobStore` against the same DB.
6. Concurrent callers for the same new `(job_id, payload)` must cause at most one
   successful handler execution and must converge on the same persisted result.
7. A handler exception must not create a successful persisted job. A later retry
   is allowed to execute the handler again.
8. Do not solve the task by using process-global state or by disabling concurrency.
9. Keep the solution local and minimal. Standard library only.

Public tests are visible. The evaluator has additional held-out tests. Do not
invent PASS for tests you did not execute.

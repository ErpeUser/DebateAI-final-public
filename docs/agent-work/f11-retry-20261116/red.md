Historical ordering mutant; not unmodified base RED.

```text
test_failed_commit_retries_identical_snapshot (test_synthesizer_commit_retry.SynthesizerCommitRetryTests.test_failed_commit_retries_identical_snapshot) ... FAIL

======================================================================
FAIL: test_failed_commit_retries_identical_snapshot (test_synthesizer_commit_retry.SynthesizerCommitRetryTests.test_failed_commit_retries_identical_snapshot)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "C:\Users\User\AppData\Local\Programs\Python\Python312\Lib\asyncio\runners.py", line 118, in run
    return self._loop.run_until_complete(task)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\User\AppData\Local\Programs\Python\Python312\Lib\asyncio\base_events.py", line 691, in run_until_complete
    return future.result()
           ^^^^^^^^^^^^^^^
  File "C:\Temp\DebateAI-agent-20261116-native\f11-retry-worktree\source\backend\tests\test_synthesizer_commit_retry.py", line 138, in test_failed_commit_retries_identical_snapshot
    self.assertEqual(1, len(applied), "identical retry must not be fingerprint-skipped")
AssertionError: 1 != 0 : identical retry must not be fingerprint-skipped

----------------------------------------------------------------------
Ran 1 test in 0.029s

FAILED (failures=1)
```

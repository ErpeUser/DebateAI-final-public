"""DA-02/03/06 lifecycle regressions; all browser and login children are fake."""

import asyncio
import subprocess
import tempfile
import threading
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest import mock


class ObservedLock(asyncio.Lock):
    def __init__(self):
        super().__init__()
        self.acquiring = asyncio.Event()

    async def acquire(self):
        self.acquiring.set()
        return await super().acquire()


class FakeAsyncChild:
    def __init__(self):
        self.returncode = None
        self.running = asyncio.Event()
        self.reaping = asyncio.Event()
        self.reap_allowed = asyncio.Event()
        self.reap_allowed.set()
        self.terminated = False

    async def communicate(self, data):
        self.running.set()
        await asyncio.Event().wait()

    def terminate(self):
        self.terminated = True

    def kill(self):
        self.terminated = True

    async def wait(self):
        self.reaping.set()
        await self.reap_allowed.wait()
        self.returncode = -15
        return self.returncode


class ServiceLifecycleTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        from app.services import chatgpt_web

        self.web = chatgpt_web
        self.stack = ExitStack()
        self.root = Path(self.stack.enter_context(tempfile.TemporaryDirectory()))
        self.lock = ObservedLock()
        self.tasks = []
        self.stack.enter_context(
            mock.patch.object(chatgpt_web, "_ORACLE_LOCK", self.lock)
        )
        self.stack.enter_context(
            mock.patch.object(chatgpt_web, "_LOGIN_RESERVED", False)
        )
        self.stack.enter_context(
            mock.patch.object(chatgpt_web, "runtime_available", return_value=True)
        )
        self.configured = self.stack.enter_context(
            mock.patch.object(chatgpt_web, "configured", return_value=True)
        )
        self.stack.enter_context(
            mock.patch.object(chatgpt_web, "_path", return_value=self.root)
        )
        self.stack.enter_context(
            mock.patch.object(chatgpt_web, "_write_research_status")
        )
        self.refusal = self.stack.enter_context(
            mock.patch.object(chatgpt_web, "_record_refusal")
        )
        self.stack.enter_context(
            mock.patch.object(
                chatgpt_web.external_audit,
                "start_external_request",
                return_value="fake-audit",
            )
        )
        self.stack.enter_context(
            mock.patch.object(chatgpt_web.external_audit, "finish_external_request")
        )
        self.spawn = self.stack.enter_context(
            mock.patch.object(
                chatgpt_web.asyncio,
                "create_subprocess_exec",
                new_callable=mock.AsyncMock,
                side_effect=AssertionError(
                    "A browser child must not be started in this case"
                ),
            )
        )

    async def asyncTearDown(self):
        for task in self.tasks:
            task.cancel()
        await asyncio.gather(*self.tasks, return_exceptions=True)
        self.stack.close()

    def task(self, coro):
        task = asyncio.create_task(coro)
        self.tasks.append(task)
        return task

    async def hold_lock(self):
        await self.lock.acquire()
        self.lock.acquiring.clear()

    async def settled(self, task, timeout=1.4):
        done, _ = await asyncio.wait({task}, timeout=timeout)
        self.assertIn(
            task,
            done,
            "adapter did not settle within its total budget plus scheduling margin",
        )
        return await task

    async def test_queued_request_rechecks_verification_before_spawn(self):
        await self.hold_lock()
        pending = self.task(self.web.generate("synthetic prompt"))
        try:
            await asyncio.wait_for(self.lock.acquiring.wait(), 1)
            self.configured.return_value = False
            self.lock.release()
            with self.assertRaisesRegex(RuntimeError, "erneut anmelden"):
                await self.settled(pending, 1)
            self.spawn.assert_not_awaited()
            self.refusal.assert_called_with("", None, "VerificationRequired")
        finally:
            if self.lock.locked() and not pending.done():
                pending.cancel()

    async def test_budget_includes_profile_queue_without_releasing_holder(self):
        await self.hold_lock()
        pending = self.task(self.web.generate("synthetic prompt", timeout_seconds=1.0))
        try:
            await asyncio.wait_for(self.lock.acquiring.wait(), 1)
            with self.assertRaises(TimeoutError):
                await self.settled(pending)
            self.assertTrue(
                self.lock.locked(), "waiter released another request's lock"
            )
            self.spawn.assert_not_awaited()
        finally:
            self.lock.release()

    async def test_queue_time_is_not_added_to_a_fresh_child_budget(self):
        child = FakeAsyncChild()
        self.spawn.side_effect = None
        self.spawn.return_value = child
        await self.hold_lock()
        pending = self.task(self.web.generate("synthetic prompt", timeout_seconds=1.0))
        await asyncio.wait_for(self.lock.acquiring.wait(), 1)

        async def release_later():
            await asyncio.sleep(0.6)
            self.lock.release()

        self.task(release_later())
        with self.assertRaises(TimeoutError):
            await self.settled(pending, 1.35)
        self.spawn.assert_awaited_once()
        self.assertTrue(child.terminated)
        self.assertIsNotNone(child.returncode)
        self.assertFalse(self.lock.locked())

    async def test_budget_includes_stalled_subprocess_creation(self):
        cancelled = asyncio.Event()

        async def never_finishes(*args, **kwargs):
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                cancelled.set()
                raise

        self.spawn.side_effect = never_finishes
        pending = self.task(self.web.generate("synthetic prompt", timeout_seconds=1.0))
        with self.assertRaises(TimeoutError):
            await self.settled(pending)
        self.assertTrue(cancelled.is_set())
        self.assertFalse(self.lock.locked())

    async def test_cancellation_keeps_profile_lock_until_child_is_reaped(self):
        child = FakeAsyncChild()
        child.reap_allowed.clear()
        self.spawn.side_effect = None
        self.spawn.return_value = child
        pending = self.task(self.web.generate("synthetic prompt"))
        try:
            await asyncio.wait_for(child.running.wait(), 1)
            pending.cancel()
            await asyncio.wait_for(child.reaping.wait(), 1)
            self.assertTrue(self.lock.locked())
            contender = self.task(self.lock.acquire())
            await asyncio.sleep(0)
            self.assertFalse(contender.done())
            child.reap_allowed.set()
            with self.assertRaises(asyncio.CancelledError):
                await pending
            await asyncio.wait_for(contender, 1)
            self.lock.release()
        finally:
            child.reap_allowed.set()

    async def test_repeated_cancellation_still_waits_for_child_cleanup(self):
        child = FakeAsyncChild()
        child.reap_allowed.clear()
        self.spawn.side_effect = None
        self.spawn.return_value = child
        pending = self.task(self.web.generate("synthetic prompt"))
        try:
            await asyncio.wait_for(child.running.wait(), 1)
            pending.cancel()
            await asyncio.wait_for(child.reaping.wait(), 1)
            pending.cancel()
            await asyncio.sleep(0)
            self.assertTrue(self.lock.locked())
            self.assertFalse(pending.done())
            child.reap_allowed.set()
            with self.assertRaises(asyncio.CancelledError):
                await pending
            self.assertFalse(self.lock.locked())
        finally:
            child.reap_allowed.set()


class FakeLoginChild:
    def __init__(self):
        self.returncode = None
        self.wait_allowed = threading.Event()
        self.wait_started = threading.Event()
        self.wait_returned = threading.Event()

    def poll(self):
        return self.returncode

    def finish(self, code=0, *, release_wait=True):
        self.returncode = code
        if release_wait:
            self.wait_allowed.set()

    def wait(self, timeout=None):
        self.wait_started.set()
        if not self.wait_allowed.wait(timeout):
            raise subprocess.TimeoutExpired("fake-login", timeout)
        self.wait_returned.set()
        return self.returncode

    def terminate(self):
        self.finish(-15)

    def kill(self):
        self.finish(-9)


class LoginLifecycleTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        from app.routers import chatgpt_web as login
        from app.services import chatgpt_web as web

        self.login, self.web = login, web
        self.stack = ExitStack()
        self.root = Path(self.stack.enter_context(tempfile.TemporaryDirectory()))
        self.result = self.root / "login-result.json"
        self.children = []
        self.existing_tasks = asyncio.all_tasks()
        self.stack.enter_context(mock.patch.object(web, "_ORACLE_LOCK", asyncio.Lock()))
        self.stack.enter_context(mock.patch.object(web, "_LOGIN_RESERVED", False))
        self.stack.enter_context(mock.patch.object(login, "_login_process", None))
        self.stack.enter_context(
            mock.patch.object(login, "_login_lock", threading.Lock())
        )
        self.stack.enter_context(
            mock.patch.object(
                login, "_configuration", return_value=(["fake-login"], self.result)
            )
        )
        self.stack.enter_context(
            mock.patch.object(
                login,
                "_status",
                side_effect=lambda *, state="idle", message="": {
                    "login_state": state,
                    "message": message,
                },
            )
        )

        def spawn(*args, **kwargs):
            child = FakeLoginChild()
            self.children.append(child)
            return child

        self.spawn = self.stack.enter_context(
            mock.patch.object(login.subprocess, "Popen", side_effect=spawn)
        )

    async def asyncTearDown(self):
        for child in self.children:
            child.finish()
        await asyncio.sleep(0.03)
        new_tasks = asyncio.all_tasks() - self.existing_tasks - {asyncio.current_task()}
        for task in new_tasks:
            task.cancel()
        await asyncio.gather(*new_tasks, return_exceptions=True)
        self.stack.close()

    async def preparation_failure_releases(self, method):
        from fastapi import HTTPException

        caught = None
        with mock.patch.object(
            Path, method, side_effect=PermissionError("synthetic denied path")
        ):
            try:
                await self.login.start_login()
            except Exception as exc:
                caught = exc
        self.assertFalse(
            self.web.browser_busy(), "failed preparation leaked the login reservation"
        )
        self.spawn.assert_not_called()
        self.assertIsInstance(caught, HTTPException)
        self.assertEqual(503, caught.status_code)

    async def test_directory_creation_failure_releases_reservation(self):
        await self.preparation_failure_releases("mkdir")

    async def test_stale_result_deletion_failure_releases_reservation(self):
        await self.preparation_failure_releases("unlink")

    async def test_spawn_failure_still_releases_reservation(self):
        from fastapi import HTTPException

        self.spawn.side_effect = OSError("synthetic spawn failure")
        with self.assertRaises(HTTPException) as raised:
            await self.login.start_login()
        self.assertEqual(503, raised.exception.status_code)
        self.assertFalse(self.web.browser_busy())

    async def test_child_exit_releases_reservation_without_ui_poll(self):
        await self.login.start_login()
        self.assertTrue(self.web.browser_busy())
        self.children[0].finish()
        deadline = asyncio.get_running_loop().time() + 1.0
        while self.web.browser_busy() and asyncio.get_running_loop().time() < deadline:
            await asyncio.sleep(0.01)
        self.assertFalse(
            self.web.browser_busy(), "completed login still depends on UI polling"
        )

    async def test_immediate_retry_reconciles_dead_previous_child(self):
        await self.login.start_login()
        self.children[0].finish(1, release_wait=False)
        response = await self.login.start_login()
        self.assertEqual("pending", response["login_state"])
        self.assertEqual(2, self.spawn.call_count)
        self.assertTrue(self.web.browser_busy())

    async def test_result_before_child_exit_does_not_release_browser(self):
        started = await self.login.start_login()
        self.assertIn("Funktionsprüfung", started["message"])
        self.result.write_text('{"verified": true}', encoding="utf-8")
        response = await self.login.poll_login()
        self.assertEqual("pending", response["login_state"])
        self.assertIn("Funktionsprüfung", response["message"])
        self.assertTrue(self.web.browser_busy())
        self.assertIsNone(self.children[0].poll())

    async def test_delayed_old_observer_cannot_release_replacement_login(self):
        await self.login.start_login()
        previous = self.children[0]
        previous.finish(1, release_wait=False)
        await self.login.start_login()
        previous.wait_allowed.set()
        await asyncio.sleep(0.35)
        self.assertIsNone(self.children[1].poll())
        self.assertTrue(
            self.web.browser_busy(),
            "old login observer released the replacement's reservation",
        )


if __name__ == "__main__":
    unittest.main()

import asyncio
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock


class ChatGPTWebProviderTests(unittest.IsolatedAsyncioTestCase):
    def _environment(self, root: Path) -> dict[str, str]:
        node = root / "node.exe"
        cli = root / "oracle-cli.js"
        marker = root / "verified.json"
        node.write_bytes(b"node")
        cli.write_text("// oracle", encoding="utf-8")
        marker.write_text("{}", encoding="utf-8")
        return {
            "DEBATEAI_CHATGPT_WEB_NODE": str(node),
            "DEBATEAI_CHATGPT_WEB_ORACLE": str(cli),
            "DEBATEAI_CHATGPT_WEB_HOME": str(root / "home"),
            "DEBATEAI_CHATGPT_WEB_PROFILE": str(root / "profile"),
            "DEBATEAI_CHATGPT_WEB_MARKER": str(marker),
        }

    def test_command_is_consumer_browser_gpt6_and_strict_pro(self):
        from app.services import chatgpt_web

        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(
            os.environ, self._environment(Path(tmp)), clear=False
        ):
            command = chatgpt_web.oracle_command(
                Path(tmp) / "answer.md", reasoning_effort="xhigh", research="search"
            )

        self.assertIn("--engine", command)
        self.assertIn("browser", command)
        self.assertIn("--browser-manual-login", command)
        self.assertIn("--model", command)
        self.assertIn("gpt-6", command)
        self.assertIn("--browser-model-strategy", command)
        self.assertEqual(
            "current",
            command[command.index("--browser-model-strategy") + 1],
        )
        self.assertIn("--browser-thinking-time", command)
        self.assertIn("extra-high", command)
        self.assertIn("--browser-research", command)
        self.assertIn("search", command)
        self.assertNotIn("api", command)

    async def test_terminate_child_reaps_after_graceful_exit(self):
        from app.services import chatgpt_web

        class Process:
            returncode = None

            def __init__(self):
                self.actions = []

            def terminate(self):
                self.actions.append("terminate")

            async def wait(self):
                self.actions.append("wait")
                self.returncode = 0

            def kill(self):
                self.actions.append("kill")

        process = Process()
        await chatgpt_web._terminate_child(process)

        self.assertEqual(["terminate", "wait"], process.actions)
        self.assertEqual(0, process.returncode)

    async def test_terminate_child_kills_after_wait_timeout(self):
        from app.services import chatgpt_web

        class Process:
            returncode = None

            def __init__(self):
                self.actions = []
                self.wait_calls = 0

            def terminate(self):
                self.actions.append("terminate")

            async def wait(self):
                self.wait_calls += 1
                self.actions.append("wait")
                if self.wait_calls == 1:
                    raise asyncio.TimeoutError
                self.returncode = -9

            def kill(self):
                self.actions.append("kill")

        process = Process()
        await chatgpt_web._terminate_child(process)

        self.assertEqual(["terminate", "wait", "kill", "wait"], process.actions)
        self.assertEqual(-9, process.returncode)

    async def test_selector_failure_blocks_followup_without_another_browser_job(self):
        from app.services import chatgpt_web

        class Process:
            returncode = 1

            async def communicate(self, prompt):
                del prompt
                return b"", b"Unable to locate the ChatGPT model selector button"

        starts = 0

        async def create(*args, **kwargs):
            nonlocal starts
            del args, kwargs
            starts += 1
            return Process()

        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(
            os.environ, self._environment(Path(tmp)), clear=False
        ), mock.patch.object(
            chatgpt_web.asyncio, "create_subprocess_exec", side_effect=create
        ):
            with self.assertRaisesRegex(RuntimeError, "model selector"):
                await chatgpt_web.generate("Erste Anfrage")
            with self.assertRaisesRegex(RuntimeError, "erneut anmelden"):
                await chatgpt_web.generate("Zweite Anfrage")
            self.assertFalse(chatgpt_web.configured())
            from app.routers import chatgpt_web as chatgpt_web_router
            status = chatgpt_web_router._status()
            self.assertFalse(status["ready"])
            self.assertIn("Erneut anmelden", status["message"])

        self.assertEqual(1, starts)

    async def test_generate_reads_oracle_output_without_exposing_cli_noise(self):
        from app.services import chatgpt_web

        class Process:
            returncode = 0

            async def communicate(self, prompt):
                output = Path(command[command.index("--write-output") + 1])
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_text("Antwort aus ChatGPT Web", encoding="utf-8")
                self.prompt = prompt
                return b"ignored", b"ignored"

        process = Process()
        command: list[str] = []

        async def create(*args, **kwargs):
            del kwargs
            command.extend(str(value) for value in args)
            return process

        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(
            os.environ, self._environment(Path(tmp)), clear=False
        ), mock.patch.object(
            chatgpt_web.asyncio, "create_subprocess_exec", side_effect=create
        ):
            answer = await chatgpt_web.generate(
                "Pruefe dieses Argument.",
                system="Antworte auf Deutsch.",
                reasoning_effort="xhigh",
            )

        self.assertEqual(answer, "Antwort aus ChatGPT Web")
        self.assertIn(b"Antworte auf Deutsch.", process.prompt)
        self.assertIn(b"Pruefe dieses Argument.", process.prompt)

    async def test_generate_serializes_the_shared_browser_profile(self):
        from app.services import chatgpt_web

        active = 0
        maximum_active = 0
        test_root = Path(__file__).parents[1] / ".test-artifacts"
        test_root.mkdir(exist_ok=True)

        class Process:
            returncode = 0

            def __init__(self, output: Path):
                self.output = output

            async def communicate(self, prompt):
                nonlocal active, maximum_active
                del prompt
                active += 1
                maximum_active = max(maximum_active, active)
                try:
                    await asyncio.sleep(0.03)
                    self.output.write_text("Antwort", encoding="utf-8")
                    return b"", b""
                finally:
                    active -= 1

        async def create(*args, **kwargs):
            del kwargs
            command = [str(value) for value in args]
            output = Path(command[command.index("--write-output") + 1])
            return Process(output)

        with mock.patch.dict(
            os.environ, self._environment(test_root), clear=False
        ), mock.patch.object(
            chatgpt_web.asyncio, "create_subprocess_exec", side_effect=create
        ):
            answers = await asyncio.gather(
                chatgpt_web.generate("Erste Anfrage"),
                chatgpt_web.generate("Zweite Anfrage"),
            )

        self.assertEqual(answers, ["Antwort", "Antwort"])
        self.assertEqual(maximum_active, 1)

    def test_research_mode_requires_an_explicit_research_request(self):
        from app.services import chatgpt_web

        ordinary_agent_prompt = (
            "Bewerte das Argument und nenne Quellen nur, wenn welche vorliegen."
        )
        self.assertIsNone(
            chatgpt_web.research_mode(
                ordinary_agent_prompt, source="consolidated_analyst"
            )
        )
        self.assertEqual(
            chatgpt_web.research_mode(
                "Recherchiere im Web nach der Originalquelle.",
                source="manual_research",
            ),
            "search",
        )

    async def test_login_reservation_blocks_model_runs(self):
        from app.services import chatgpt_web

        test_root = Path(__file__).parents[1] / ".test-artifacts-login"
        test_root.mkdir(exist_ok=True)
        environment = self._environment(test_root)
        self.assertTrue(chatgpt_web.reserve_login())
        try:
            with mock.patch.dict(os.environ, environment, clear=False):
                with self.assertRaisesRegex(RuntimeError, "Anmeldung"):
                    await chatgpt_web.generate("Diese Anfrage darf nicht starten.")
        finally:
            chatgpt_web.release_login()

    def test_llm_routes_consumer_web_model_separately_from_codex_oauth(self):
        from app.services.llm import provider_for

        self.assertEqual(provider_for("chatgpt-web:gpt-6"), "chatgpt-web")
        self.assertEqual(
            provider_for("endpoint:subscription-ai:gpt-6-sol"),
            "openai-compatible",
        )


if __name__ == "__main__":
    unittest.main()

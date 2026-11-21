import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from debateai_desktop import chatgpt_web_login


class ChatGPTWebLoginTests(unittest.TestCase):
    def test_verified_ui_selection_is_saved_even_when_answer_file_is_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            node = root / "node.exe"
            cli = root / "oracle.js"
            node.write_bytes(b"node")
            cli.write_text("// oracle", encoding="utf-8")
            result = root / "result.json"
            marker = root / "verified.json"
            output = root / "home" / "login-verification.md"

            def completed(command, **kwargs):
                del command, kwargs
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_text("", encoding="utf-8")
                session = root / "home" / "sessions" / "proof"
                session.mkdir(parents=True, exist_ok=True)
                (session / "meta.json").write_text(json.dumps({
                    "browser": {
                        "modelSelection": {"verified": True, "resolvedLabel": "GPT-6"},
                        "thinkingSelection": {
                            "verified": True,
                            "requestedLevel": "extra-high",
                            "resolvedLabel": "Extra High",
                        },
                    }
                }), encoding="utf-8")
                return mock.Mock(returncode=0)

            env = {
                "DEBATEAI_CHATGPT_WEB_NODE": str(node),
                "DEBATEAI_CHATGPT_WEB_ORACLE": str(cli),
                "DEBATEAI_CHATGPT_WEB_HOME": str(root / "home"),
                "DEBATEAI_CHATGPT_WEB_PROFILE": str(root / "profile"),
                "DEBATEAI_CHATGPT_WEB_MARKER": str(marker),
            }
            with mock.patch.dict(os.environ, env, clear=False), mock.patch.object(
                chatgpt_web_login.subprocess, "run", side_effect=completed
            ):
                code = chatgpt_web_login.run_chatgpt_web_login(result)

            self.assertEqual(0, code)
            evidence = json.loads(marker.read_text(encoding="utf-8"))
            self.assertFalse(evidence["answer_received"])
            self.assertEqual("gpt-6", evidence["actual_model"])

    def test_success_writes_only_non_secret_verification_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            node = root / "node.exe"
            cli = root / "oracle.js"
            node.write_bytes(b"node")
            cli.write_text("// oracle", encoding="utf-8")
            result = root / "result.json"
            marker = root / "verified.json"
            output = root / "home" / "login-verification.md"

            def completed(command, **kwargs):
                del command, kwargs
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_text("OK", encoding="utf-8")
                session = root / "home" / "sessions" / "proof"
                session.mkdir(parents=True, exist_ok=True)
                (session / "meta.json").write_text(json.dumps({
                    "browser": {
                        "modelSelection": {
                            "verified": True,
                            "resolvedLabel": "GPT-6",
                        },
                        "thinkingSelection": {
                            "verified": True,
                            "requestedLevel": "extra-high",
                            "resolvedLabel": "Extra High",
                        },
                    }
                }), encoding="utf-8")
                return mock.Mock(returncode=0)

            env = {
                "DEBATEAI_CHATGPT_WEB_NODE": str(node),
                "DEBATEAI_CHATGPT_WEB_ORACLE": str(cli),
                "DEBATEAI_CHATGPT_WEB_HOME": str(root / "home"),
                "DEBATEAI_CHATGPT_WEB_PROFILE": str(root / "profile"),
                "DEBATEAI_CHATGPT_WEB_MARKER": str(marker),
            }
            with mock.patch.dict(os.environ, env, clear=False), mock.patch.object(
                chatgpt_web_login.subprocess, "run", side_effect=completed
            ):
                code = chatgpt_web_login.run_chatgpt_web_login(result)

            self.assertEqual(0, code)
            evidence = json.loads(marker.read_text(encoding="utf-8"))
            self.assertEqual("gpt-6", evidence["actual_model"])
            self.assertEqual("xhigh", evidence["thinking"])
            self.assertIs(evidence["answer_received"], True)
            self.assertNotIn("cookie", json.dumps(evidence).casefold())
            self.assertFalse(output.exists())

    def test_latest_label_is_not_treated_as_confirmed_gpt6(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            home = root / "home"
            session = home / "sessions" / "proof"
            session.mkdir(parents=True, exist_ok=True)
            metadata = {
                "browser": {
                    "modelSelection": {
                        "verified": True,
                        "resolvedLabel": "Latest",
                    },
                    "thinkingSelection": {
                        "verified": True,
                        "requestedLevel": "extra-high",
                    },
                }
            }
            (session / "meta.json").write_text(json.dumps(metadata), encoding="utf-8")
            self.assertIsNone(
                chatgpt_web_login._verified_oracle_selection(
                    home,
                    started_at=0,
                )
            )

    def test_failure_does_not_enable_provider(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            node = root / "node.exe"
            cli = root / "oracle.js"
            node.write_bytes(b"node")
            cli.write_text("// oracle", encoding="utf-8")
            marker = root / "verified.json"
            env = {
                "DEBATEAI_CHATGPT_WEB_NODE": str(node),
                "DEBATEAI_CHATGPT_WEB_ORACLE": str(cli),
                "DEBATEAI_CHATGPT_WEB_HOME": str(root / "home"),
                "DEBATEAI_CHATGPT_WEB_PROFILE": str(root / "profile"),
                "DEBATEAI_CHATGPT_WEB_MARKER": str(marker),
            }
            with mock.patch.dict(os.environ, env, clear=False), mock.patch.object(
                chatgpt_web_login.subprocess, "run", return_value=mock.Mock(returncode=1)
            ):
                code = chatgpt_web_login.run_chatgpt_web_login(root / "result.json")
            self.assertEqual(1, code)
            self.assertFalse(marker.exists())

    def test_failure_does_not_persist_oracle_diagnostics(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            node = root / "node.exe"
            cli = root / "oracle.js"
            node.write_bytes(b"node")
            cli.write_text("// oracle", encoding="utf-8")
            result = root / "result.json"
            env = {
                "DEBATEAI_CHATGPT_WEB_NODE": str(node),
                "DEBATEAI_CHATGPT_WEB_ORACLE": str(cli),
                "DEBATEAI_CHATGPT_WEB_HOME": str(root / "home"),
                "DEBATEAI_CHATGPT_WEB_PROFILE": str(root / "profile"),
                "DEBATEAI_CHATGPT_WEB_MARKER": str(root / "verified.json"),
            }
            completed = mock.Mock(
                returncode=1,
                stderr="cookie=secret-provider-response",
                stdout="account@example.com",
            )
            with mock.patch.dict(os.environ, env, clear=False), mock.patch.object(
                chatgpt_web_login.subprocess, "run", return_value=completed
            ):
                code = chatgpt_web_login.run_chatgpt_web_login(result)
            self.assertEqual(1, code)
            payload = json.loads(result.read_text(encoding="utf-8"))
            serialized = json.dumps(payload)
            self.assertNotIn("secret-provider-response", serialized)
            self.assertNotIn("account@example.com", serialized)
            self.assertEqual("Die ChatGPT-Web-Prüfung konnte nicht abgeschlossen werden.", payload["error"])


if __name__ == "__main__":
    unittest.main()

import json
from unittest import IsolatedAsyncioTestCase
from unittest.mock import patch

from scripts import replay_call


class ReplayCallStatusTests(IsolatedAsyncioTestCase):
    async def test_reports_current_diarization_overflow_status(self):
        class FakeWebSocket:
            def __aiter__(self):
                async def messages():
                    yield json.dumps(
                        {
                            "type": "status",
                            "data": {
                                "state": "diarization_overflow",
                                "message": "queue full",
                            },
                        }
                    )

                return messages()

        with patch("builtins.print") as print_mock:
            await replay_call._drain_server_messages(FakeWebSocket(), {})

        self.assertTrue(
            any("diarization_overflow" in str(call) for call in print_mock.call_args_list)
        )

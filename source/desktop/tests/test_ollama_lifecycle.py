import unittest
from pathlib import Path

from bcdesktop.ollama_lifecycle import ManagedOllama


class _Process:
    def __init__(self):
        self.terminated = False
        self.waited = False

    def poll(self):
        return None

    def terminate(self):
        self.terminated = True

    def wait(self, timeout=None):
        self.waited = True
        return 0


class ManagedOllamaTests(unittest.TestCase):
    def test_existing_server_is_never_stopped_by_the_app(self):
        launches = []
        manager = ManagedOllama(
            executable=Path("ollama.exe"),
            probe=lambda: True,
            process_factory=lambda *args, **kwargs: launches.append((args, kwargs)),
        )

        self.assertEqual("already_running", manager.start())
        manager.stop()

        self.assertEqual([], launches)
        self.assertFalse(manager.owns_process)

    def test_server_started_by_the_app_is_stopped_on_exit(self):
        process = _Process()
        probes = iter((False, True))
        manager = ManagedOllama(
            executable=Path("ollama.exe"),
            probe=lambda: next(probes, True),
            process_factory=lambda *args, **kwargs: process,
            sleep=lambda _seconds: None,
        )

        self.assertEqual("started", manager.start(timeout=1))
        self.assertTrue(manager.owns_process)

        manager.stop()

        self.assertTrue(process.terminated)
        self.assertTrue(process.waited)
        self.assertFalse(manager.owns_process)

    def test_missing_executable_keeps_cloud_and_remote_models_available(self):
        manager = ManagedOllama(executable=None, probe=lambda: False)

        self.assertEqual("unavailable", manager.start())
        self.assertFalse(manager.owns_process)

    def test_external_server_releases_only_models_loaded_during_this_app_run(self):
        snapshots = iter(({"shared-model"}, {"shared-model", "qwen3:4b"}))
        unloaded = []
        manager = ManagedOllama(
            executable=None,
            probe=lambda: True,
            loaded_models=lambda: next(snapshots),
            unload_model=unloaded.append,
        )

        self.assertEqual("already_running", manager.start())
        manager.stop()

        self.assertEqual(["qwen3:4b"], unloaded)
        self.assertFalse(manager.owns_process)


if __name__ == "__main__":
    unittest.main()

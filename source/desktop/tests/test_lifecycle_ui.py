import unittest

from bcdesktop.lifecycle_ui import LifecycleSplash


class _Window:
    def __init__(self):
        self.title = ""
        self.detail = ""
        self.progress = 0
        self.closed = False

    def show(self, title, detail):
        self.title = title
        self.detail = detail

    def set_detail(self, detail):
        self.detail = detail

    def set_progress(self, progress, detail=None):
        self.progress = progress
        if detail is not None:
            self.detail = detail

    def close(self):
        self.closed = True


class LifecycleSplashTests(unittest.TestCase):
    def test_start_and_shutdown_have_clear_german_status(self):
        window = _Window()
        splash = LifecycleSplash(window_factory=lambda: window)

        splash.show_startup("Datenbank wird gestartet ...")
        self.assertEqual("Debate AI wird gestartet", window.title)
        self.assertEqual("Datenbank wird gestartet ...", window.detail)
        self.assertEqual(2, window.progress)

        splash.show_shutdown("Lokales KI-Modell wird beendet ...")
        self.assertEqual("Debate AI wird beendet", window.title)
        self.assertEqual("Lokales KI-Modell wird beendet ...", window.detail)
        self.assertEqual(5, window.progress)

        splash.close()
        self.assertTrue(window.closed)

    def test_unavailable_gui_never_blocks_the_launcher(self):
        splash = LifecycleSplash(window_factory=lambda: (_ for _ in ()).throw(RuntimeError("no GUI")))

        splash.show_startup("Start")
        splash.set_detail("Weiter")
        splash.show_shutdown("Ende")
        splash.close()

        self.assertFalse(splash.visible)


if __name__ == "__main__":
    unittest.main()

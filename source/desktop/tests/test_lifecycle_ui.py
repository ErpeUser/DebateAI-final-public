import sys
import unittest
from unittest import mock

from debateai_desktop import lifecycle_ui
from debateai_desktop.lifecycle_ui import LifecycleSplash


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

    def test_window_runtime_failure_never_blocks_the_launcher(self):
        class _BrokenWindow(_Window):
            def show(self, title, detail):
                super().show(title, detail)
                raise RuntimeError("display closed")

        window = _BrokenWindow()
        splash = LifecycleSplash(window_factory=lambda: window)

        splash.show_startup("Start")
        splash.show_shutdown("Ende")
        splash.set_detail("Weiter")
        splash.set_progress(50)
        splash.close()

        self.assertTrue(window.closed)
        self.assertFalse(splash.visible)

    def test_detail_failure_closes_and_releases_the_window(self):
        class _BrokenDetailWindow(_Window):
            def set_detail(self, detail):
                raise RuntimeError("display closed")

        window = _BrokenDetailWindow()
        splash = LifecycleSplash(window_factory=lambda: window)
        splash.show_startup("Start")
        splash.set_detail("Weiter")

        self.assertTrue(window.closed)
        self.assertFalse(splash.visible)

    def test_unavailable_gui_never_blocks_the_launcher(self):
        splash = LifecycleSplash(window_factory=lambda: (_ for _ in ()).throw(RuntimeError("no GUI")))

        splash.show_startup("Start")
        splash.set_detail("Weiter")
        splash.show_shutdown("Ende")
        splash.close()

        self.assertFalse(splash.visible)

    def test_tk_constructor_destroys_root_when_setup_fails(self):
        destroyed = []

        class Root:
            def title(self, _value): pass
            def configure(self, **_kwargs): pass
            def resizable(self, *_args): pass
            def attributes(self, *_args): pass
            def overrideredirect(self, *_args): pass
            def winfo_screenwidth(self): return 1000
            def winfo_screenheight(self): return 800
            def geometry(self, _value): pass
            def update_idletasks(self): raise RuntimeError("display vanished")
            def update(self): pass
            def destroy(self): destroyed.append(True)

        class Widget:
            def __init__(self, *_args, **_kwargs): pass
            def pack(self, **_kwargs): return self
            def pack_propagate(self, *_args): pass
            def configure(self, **_kwargs): pass

        fake_tk = type("Tk", (), {"Tk": staticmethod(Root), "Frame": Widget, "Label": Widget})
        with mock.patch.dict(sys.modules, {"tkinter": fake_tk}):
            with self.assertRaisesRegex(RuntimeError, "display vanished"):
                lifecycle_ui._TkLifecycleWindow()
        self.assertEqual(destroyed, [True])


if __name__ == "__main__":
    unittest.main()

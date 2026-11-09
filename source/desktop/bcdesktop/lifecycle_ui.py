"""Small native startup/shutdown window for the desktop lifecycle."""

from __future__ import annotations

from typing import Callable


class _TkLifecycleWindow:
    def __init__(self) -> None:
        import tkinter as tk

        self._tk = tk
        root = tk.Tk()
        self._root = root
        root.title("Debate AI")
        root.configure(bg="#050505")
        root.resizable(False, False)
        root.attributes("-topmost", True)
        root.overrideredirect(True)

        width, height = 520, 270
        x = max(0, (root.winfo_screenwidth() - width) // 2)
        y = max(0, (root.winfo_screenheight() - height) // 2)
        root.geometry(f"{width}x{height}+{x}+{y}")

        frame = tk.Frame(root, bg="#111111", highlightbackground="#3f3f46", highlightthickness=1)
        frame.pack(fill="both", expand=True, padx=1, pady=1)
        tk.Label(
            frame,
            text="DEBATE AI",
            bg="#111111",
            fg="#f4f4f5",
            font=("Segoe UI Semibold", 11),
            anchor="w",
        ).pack(fill="x", padx=34, pady=(34, 6))
        self._title = tk.Label(
            frame,
            text="",
            bg="#111111",
            fg="#f5f8fc",
            font=("Segoe UI Semibold", 22),
            anchor="w",
        )
        self._title.pack(fill="x", padx=34, pady=(0, 10))
        self._detail = tk.Label(
            frame,
            text="",
            bg="#111111",
            fg="#a1a1aa",
            font=("Segoe UI", 11),
            anchor="w",
        )
        self._detail.pack(fill="x", padx=34)
        self._track_width = 452
        track = tk.Frame(frame, bg="#27272a", width=self._track_width, height=6)
        track.pack(fill="x", padx=34, pady=(30, 8))
        track.pack_propagate(False)
        self._bar = tk.Frame(track, bg="#f4f4f5", width=1, height=6)
        self._bar.pack(side="left")
        self._progress = tk.Label(
            frame,
            text="0 %",
            bg="#111111",
            fg="#a1a1aa",
            font=("Segoe UI Semibold", 9),
            anchor="e",
        )
        self._progress.pack(fill="x", padx=34)
        tk.Label(
            frame,
            text="Datenbank und KI laufen nur, solange Debate AI aktiv ist.",
            bg="#111111",
            fg="#71717a",
            font=("Segoe UI", 9),
            anchor="w",
        ).pack(fill="x", padx=34)
        root.update_idletasks()
        root.update()

    def show(self, title: str, detail: str) -> None:
        self._title.configure(text=title)
        self._detail.configure(text=detail)
        self._root.deiconify()
        self._root.lift()
        self._root.update_idletasks()
        self._root.update()

    def set_detail(self, detail: str) -> None:
        self._detail.configure(text=detail)
        self._root.update_idletasks()
        self._root.update()

    def set_progress(self, progress: int, detail: str | None = None) -> None:
        value = max(0, min(100, int(progress)))
        if detail is not None:
            self._detail.configure(text=detail)
        self._bar.configure(width=max(1, round(self._track_width * value / 100)))
        self._progress.configure(text=f"{value} %")
        self._root.update_idletasks()
        self._root.update()

    def close(self) -> None:
        self._root.destroy()


class LifecycleSplash:
    """Best-effort presenter; GUI failures never block application startup."""

    def __init__(self, window_factory: Callable[[], object] = _TkLifecycleWindow) -> None:
        self._window_factory = window_factory
        self._window = None

    @property
    def visible(self) -> bool:
        return self._window is not None

    def _ensure_window(self):
        if self._window is None:
            try:
                self._window = self._window_factory()
            except Exception:
                self._window = None
        return self._window

    def show_startup(self, detail: str) -> None:
        window = self._ensure_window()
        if window is not None:
            window.show("Debate AI wird gestartet", detail)
            window.set_progress(2)

    def show_shutdown(self, detail: str) -> None:
        window = self._ensure_window()
        if window is not None:
            window.show("Debate AI wird beendet", detail)
            window.set_progress(5)

    def set_detail(self, detail: str) -> None:
        if self._window is not None:
            try:
                self._window.set_detail(detail)
            except Exception:
                self._window = None

    def set_progress(self, progress: int, detail: str | None = None) -> None:
        if self._window is not None:
            try:
                self._window.set_progress(progress, detail)
            except Exception:
                self._window = None

    def close(self) -> None:
        window, self._window = self._window, None
        if window is not None:
            try:
                window.close()
            except Exception:
                pass

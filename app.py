from __future__ import annotations

import os
import queue
import shutil
import sys
import tempfile
import threading
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk

# When bundled by PyInstaller, inject bundled ffmpeg/ffprobe into PATH
if getattr(sys, "frozen", False):
    _bin_dir = Path(sys._MEIPASS) / "bin"
    os.environ["PATH"] = str(_bin_dir) + os.pathsep + os.environ.get("PATH", "")

from scripts.core import ProcessConfig, process_video

SUPPORTED = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v", ".mts", ".ts"}
DARK_BG = "#1e1e1e"
DARK_FG = "#d4d4d4"


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Pause Remover")
        self.resizable(False, False)
        self._input_path: Path | None = None
        self._tmp_out: Path | None = None
        self._log_queue: queue.Queue[str | None] = queue.Queue()
        self._processing = False
        self._build_ui()

    def _build_ui(self) -> None:
        outer = {"padx": 14, "pady": 6}

        # ── File picker ───────────────────────────────────────────
        file_frame = tk.Frame(self)
        file_frame.pack(fill="x", **outer)
        tk.Label(file_frame, text="Video:", width=6, anchor="w").pack(side="left")
        self._file_label = tk.Label(
            file_frame, text="No file selected", anchor="w", fg="gray", width=38
        )
        self._file_label.pack(side="left", expand=True, fill="x")
        tk.Button(file_frame, text="Browse…", command=self._browse).pack(side="right")

        # ── Settings ──────────────────────────────────────────────
        sf = tk.LabelFrame(self, text="Settings", padx=10, pady=6)
        sf.pack(fill="x", padx=14, pady=4)
        self._noise_db = self._slider_row(sf, "Silence threshold", -60, -10, -30, "dB", 0, res=1)
        self._min_pause = self._slider_row(sf, "Min pause duration", 0.5, 10.0, 2.0, "s", 1, res=0.5)
        self._padding   = self._slider_row(sf, "Padding",           0.0,  1.0, 0.4, "s", 2, res=0.05)

        # ── Action button ─────────────────────────────────────────
        bf = tk.Frame(self)
        bf.pack(fill="x", padx=14, pady=6)
        self._btn = tk.Button(
            bf,
            text="Remove Pauses",
            command=self._start,
            state="disabled",
            bg="#2563eb",
            fg="white",
            font=("", 13, "bold"),
            pady=8,
            relief="flat",
        )
        self._btn.pack(fill="x")

        # ── Progress bar ──────────────────────────────────────────
        self._progress = ttk.Progressbar(self, mode="indeterminate", length=400)
        self._progress.pack(fill="x", padx=14, pady=(0, 4))

        # ── Log ───────────────────────────────────────────────────
        lf = tk.LabelFrame(self, text="Log", padx=4, pady=4)
        lf.pack(fill="both", expand=True, padx=14, pady=(0, 14))
        self._log = scrolledtext.ScrolledText(
            lf,
            height=10,
            state="disabled",
            font=("Menlo", 10),
            bg=DARK_BG,
            fg=DARK_FG,
            wrap="word",
        )
        self._log.pack(fill="both", expand=True)

        self.geometry("540x500")

    def _slider_row(
        self,
        parent: tk.Widget,
        label: str,
        from_: float,
        to: float,
        default: float,
        unit: str,
        row: int,
        res: float = 1.0,
    ) -> tk.DoubleVar:
        tk.Label(parent, text=label, width=20, anchor="w").grid(
            row=row, column=0, sticky="w", pady=3
        )
        var = tk.DoubleVar(value=default)
        val_lbl = tk.Label(parent, text=f"{default:.2f} {unit}", width=10, anchor="e")
        val_lbl.grid(row=row, column=2, sticky="e")

        def _update(v: str) -> None:
            val_lbl.config(text=f"{float(v):.2f} {unit}")

        tk.Scale(
            parent,
            from_=from_,
            to=to,
            orient="horizontal",
            variable=var,
            resolution=res,
            showvalue=False,
            command=_update,
            length=240,
        ).grid(row=row, column=1, sticky="ew", padx=8)
        parent.columnconfigure(1, weight=1)
        return var

    def _browse(self) -> None:
        path = filedialog.askopenfilename(
            title="Select a video file",
            filetypes=[
                ("Video files", "*.mp4 *.mov *.mkv *.avi *.webm *.m4v *.mts *.ts"),
                ("All files", "*.*"),
            ],
        )
        if not path:
            return
        p = Path(path)
        if p.suffix.lower() not in SUPPORTED:
            messagebox.showerror("Unsupported format", f"'{p.suffix}' is not supported.")
            return
        self._input_path = p
        self._file_label.config(text=p.name, fg="black")
        self._btn.config(state="normal")

    def _start(self) -> None:
        if self._processing or not self._input_path:
            return
        self._processing = True
        self._btn.config(state="disabled")
        self._log_clear()
        self._progress.start(12)

        suffix = self._input_path.suffix
        fd, tmp_path = tempfile.mkstemp(suffix=f"_no_pauses{suffix}")
        os.close(fd)
        self._tmp_out = Path(tmp_path)

        config = ProcessConfig(
            input_path=self._input_path,
            output_path=self._tmp_out,
            noise_db=self._noise_db.get(),
            min_pause=self._min_pause.get(),
            padding=self._padding.get(),
        )

        threading.Thread(target=self._worker, args=(config,), daemon=True).start()
        self.after(100, self._poll)

    def _worker(self, config: ProcessConfig) -> None:
        try:
            process_video(config, log_callback=self._log_queue.put)
            self._log_queue.put(None)  # success sentinel
        except Exception as exc:
            self._log_queue.put(f"ERROR: {exc}")
            self._log_queue.put("__FAIL__")

    def _poll(self) -> None:
        done = failed = False
        while not self._log_queue.empty():
            msg = self._log_queue.get_nowait()
            if msg is None:
                done = True
            elif msg == "__FAIL__":
                failed = True
            else:
                self._log_append(msg)
        if done:
            self._on_success()
        elif failed:
            self._on_failure()
        else:
            self.after(100, self._poll)

    def _on_success(self) -> None:
        self._progress.stop()
        self._processing = False
        self._btn.config(state="normal")

        suffix = self._input_path.suffix
        save_path = filedialog.asksaveasfilename(
            title="Save edited video",
            defaultextension=suffix,
            initialfile=f"{self._input_path.stem}_no_pauses{suffix}",
            filetypes=[("Video", f"*{suffix}"), ("All files", "*.*")],
        )
        if save_path:
            shutil.move(str(self._tmp_out), save_path)
            self._log_append(f"\nSaved → {save_path}")
            messagebox.showinfo("Done", f"Saved to:\n{save_path}")
        else:
            if self._tmp_out and self._tmp_out.exists():
                self._tmp_out.unlink()
            self._log_append("\nSave cancelled.")

    def _on_failure(self) -> None:
        self._progress.stop()
        self._processing = False
        self._btn.config(state="normal")
        if self._tmp_out and self._tmp_out.exists():
            self._tmp_out.unlink()
        messagebox.showerror("Processing failed", "Check the log for details.")

    def _log_append(self, text: str) -> None:
        self._log.config(state="normal")
        self._log.insert("end", text + "\n")
        self._log.see("end")
        self._log.config(state="disabled")

    def _log_clear(self) -> None:
        self._log.config(state="normal")
        self._log.delete("1.0", "end")
        self._log.config(state="disabled")


if __name__ == "__main__":
    App().mainloop()

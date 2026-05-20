"""Tkinter desktop UI for Universal Media Converter.

Copyright 2026 Frost Forge Labs Inc.
https://frostforgelabs.ca
Licensed under the Apache License, Version 2.0.
"""

from __future__ import annotations

import os
import queue
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Callable

from .cli import parse_formats
from .converter import MediaConverter
from .ffmpeg_manager import FFmpegManager
from .logging_setup import setup_logging
from .models import ConversionConfig, ConversionResult
from .reporting import summarize_results, write_reports

COMMON_FORMATS = ("mp4", "mkv", "mov", "webm", "mp3", "m4a", "wav", "flac", "aac")
QUEUE_DRAIN_LIMIT = 50


class ConverterApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Universal Media Converter")
        self.geometry("940x660")
        self.resizable(True, True)
        self.event_queue: queue.Queue[ConversionResult | tuple[str, object]] = queue.Queue()
        self.worker: threading.Thread | None = None
        self._is_closing = False
        self._poll_after_id: str | None = None
        self._modal_after_ids: list[str] = []
        self._total_jobs = 0
        self._completed_jobs = 0

        self.input_var = tk.StringVar()
        self.output_var = tk.StringVar()
        self.crf_var = tk.IntVar(value=18)
        self.preset_var = tk.StringVar(value="slow")
        self.audio_bitrate_var = tk.StringVar(value="192k")
        self.overwrite_var = tk.BooleanVar(value=False)
        self.recursive_var = tk.BooleanVar(value=True)
        self.preserve_structure_var = tk.BooleanVar(value=True)
        self.copy_same_var = tk.BooleanVar(value=True)
        self.all_files_var = tk.BooleanVar(value=False)
        self.custom_formats_var = tk.StringVar(value="")
        self.format_vars = {fmt: tk.BooleanVar(value=(fmt == "mp4")) for fmt in COMMON_FORMATS}

        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._bring_to_front()
        self._schedule_poll()

    def _build_ui(self) -> None:
        padding = {"padx": 10, "pady": 6}
        root = ttk.Frame(self)
        root.pack(fill="both", expand=True, padx=14, pady=14)

        ttk.Label(root, text="Input Directory").grid(row=0, column=0, sticky="w", **padding)
        ttk.Entry(root, textvariable=self.input_var).grid(row=0, column=1, sticky="ew", **padding)
        ttk.Button(root, text="Browse", command=lambda: self._choose_dir(self.input_var)).grid(row=0, column=2, **padding)

        ttk.Label(root, text="Output Directory").grid(row=1, column=0, sticky="w", **padding)
        ttk.Entry(root, textvariable=self.output_var).grid(row=1, column=1, sticky="ew", **padding)
        ttk.Button(root, text="Browse", command=lambda: self._choose_dir(self.output_var)).grid(row=1, column=2, **padding)

        formats = ttk.LabelFrame(root, text="Output Formats")
        formats.grid(row=2, column=0, columnspan=3, sticky="ew", padx=10, pady=10)
        for idx, fmt in enumerate(COMMON_FORMATS):
            ttk.Checkbutton(formats, text=fmt.upper(), variable=self.format_vars[fmt]).grid(
                row=idx // 6, column=idx % 6, sticky="w", **padding
            )
        ttk.Label(formats, text="Custom, comma-separated").grid(row=2, column=0, sticky="w", **padding)
        ttk.Entry(formats, textvariable=self.custom_formats_var).grid(row=2, column=1, columnspan=5, sticky="ew", **padding)
        formats.columnconfigure(5, weight=1)

        options = ttk.LabelFrame(root, text="Conversion Options")
        options.grid(row=3, column=0, columnspan=3, sticky="ew", padx=10, pady=10)
        ttk.Label(options, text="CRF Quality").grid(row=0, column=0, sticky="w", **padding)
        ttk.Spinbox(options, from_=0, to=51, textvariable=self.crf_var, width=8).grid(row=0, column=1, sticky="w", **padding)
        ttk.Label(options, text="Preset").grid(row=0, column=2, sticky="w", **padding)
        ttk.Combobox(options, textvariable=self.preset_var, values=("ultrafast", "superfast", "veryfast", "faster", "fast", "medium", "slow", "slower", "veryslow"), width=12).grid(row=0, column=3, sticky="w", **padding)
        ttk.Label(options, text="Audio Bitrate").grid(row=0, column=4, sticky="w", **padding)
        ttk.Entry(options, textvariable=self.audio_bitrate_var, width=10).grid(row=0, column=5, sticky="w", **padding)

        ttk.Checkbutton(options, text="Scan subfolders", variable=self.recursive_var).grid(row=1, column=0, sticky="w", **padding)
        ttk.Checkbutton(options, text="Preserve folder structure", variable=self.preserve_structure_var).grid(row=1, column=1, sticky="w", **padding)
        ttk.Checkbutton(options, text="Overwrite", variable=self.overwrite_var).grid(row=1, column=2, sticky="w", **padding)
        ttk.Checkbutton(options, text="Copy same-format files", variable=self.copy_same_var).grid(row=1, column=3, sticky="w", **padding)
        ttk.Checkbutton(options, text="Attempt all files", variable=self.all_files_var).grid(row=1, column=4, sticky="w", **padding)

        self.start_button = ttk.Button(root, text="Start Conversion", command=self._start)
        self.start_button.grid(row=4, column=0, sticky="w", **padding)
        self.status_label = ttk.Label(root, text="Ready")
        self.status_label.grid(row=4, column=1, columnspan=2, sticky="w", **padding)

        progress_frame = ttk.Frame(root)
        progress_frame.grid(row=5, column=0, columnspan=3, sticky="ew", padx=10, pady=(0, 4))
        self.progress_bar = ttk.Progressbar(progress_frame, mode="determinate", maximum=100)
        self.progress_bar.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.progress_label = ttk.Label(progress_frame, text="", width=24, anchor="e")
        self.progress_label.pack(side="right")

        self.log_box = tk.Text(root, height=20, wrap="word")
        self.log_box.grid(row=6, column=0, columnspan=3, sticky="nsew", padx=10, pady=(0, 10))
        root.columnconfigure(1, weight=1)
        root.rowconfigure(6, weight=1)

    def _choose_dir(self, var: tk.StringVar) -> None:
        selected = filedialog.askdirectory()
        if selected:
            var.set(selected)

    def _selected_formats(self) -> tuple[str, ...]:
        selected = [fmt for fmt, var in self.format_vars.items() if var.get()]
        selected.extend(parse_formats(self.custom_formats_var.get()))
        deduped: list[str] = []
        for fmt in selected:
            if fmt and fmt not in deduped:
                deduped.append(fmt)
        return tuple(deduped)

    def _start(self) -> None:
        if self.worker and self.worker.is_alive():
            return
        input_value = self.input_var.get().strip()
        output_value = self.output_var.get().strip()
        if not input_value:
            messagebox.showerror("Invalid input", "Please select a valid input directory.")
            return
        if not output_value:
            messagebox.showerror("Invalid output", "Please select an output directory.")
            return

        input_dir = Path(input_value).expanduser()
        output_dir = Path(output_value).expanduser()
        output_formats = self._selected_formats()
        if not input_dir.exists():
            messagebox.showerror("Invalid input", "Please select a valid input directory.")
            return
        if input_dir.resolve() == output_dir.resolve():
            messagebox.showerror("Invalid output", "Input and output directories must be different.")
            return
        if not output_formats:
            messagebox.showerror("Invalid formats", "Select at least one output format.")
            return

        self.start_button.configure(state="disabled")
        self.status_label.configure(text="Working...")
        self.log_box.delete("1.0", "end")
        self._total_jobs = 0
        self._completed_jobs = 0
        self.progress_bar["value"] = 0
        self.progress_label.configure(text="")
        config = ConversionConfig(
            input_dir=input_dir,
            output_dir=output_dir,
            recursive=self.recursive_var.get(),
            overwrite=self.overwrite_var.get(),
            crf=self.crf_var.get(),
            preset=self.preset_var.get(),
            audio_bitrate=self.audio_bitrate_var.get(),
            preserve_structure=self.preserve_structure_var.get(),
            copy_same_extension=self.copy_same_var.get(),
            output_formats=output_formats,
            scan_all_files=self.all_files_var.get(),
        )
        self.worker = threading.Thread(target=self._run_conversion, args=(output_dir, config), daemon=True)
        self.worker.start()

    def _run_conversion(self, output_dir: Path, config: ConversionConfig) -> None:
        try:
            setup_logging(output_dir / "logs")
            manager = FFmpegManager()
            ffmpeg_path = manager.get_ffmpeg_path(auto_prepare=True)
            converter = MediaConverter(ffmpeg_path)
            total = len(converter.discover_files(config)) * len(config.normalized_output_formats())
            self.event_queue.put(("total", total))

            def _on_job_start(job_num: int, source: Path) -> None:
                self.event_queue.put(("job_start", (job_num, source.name)))

            results = converter.convert_directory(
                config,
                progress_callback=self.event_queue.put,
                start_callback=_on_job_start,
            )
            reports = write_reports(results, output_dir / "reports")
            self.event_queue.put(("done", (results, reports)))
        except Exception as exc:
            self.event_queue.put(("error", exc))

    def _poll_queue(self) -> None:
        if self._is_closing:
            return
        pending_log_lines: list[str] = []
        drained = 0
        try:
            while drained < QUEUE_DRAIN_LIMIT:
                item = self.event_queue.get_nowait()
                drained += 1
                if isinstance(item, ConversionResult):
                    pending_log_lines.append(
                        f"{item.status.upper()}: {item.action} -> {item.output_format} | "
                        f"{item.source.name} | {item.message}\n"
                    )
                    self._completed_jobs += 1
                    if self._total_jobs > 0:
                        pct = int(self._completed_jobs * 100 / self._total_jobs)
                        self.progress_bar["value"] = pct
                        self.progress_label.configure(
                            text=f"{self._completed_jobs} / {self._total_jobs}  ({pct}%)"
                        )
                elif isinstance(item, tuple):
                    kind, payload = item
                    if pending_log_lines:
                        self._append_log("".join(pending_log_lines))
                        pending_log_lines.clear()
                    if kind == "total":
                        self._total_jobs = int(payload)
                        self._completed_jobs = 0
                        self.progress_bar["value"] = 0
                        self.progress_label.configure(
                            text=f"0 / {self._total_jobs}  (0%)" if self._total_jobs > 0 else "No files found"
                        )
                    elif kind == "job_start":
                        job_num, name = payload
                        stem = name if len(name) <= 60 else name[:57] + "..."
                        self.status_label.configure(text=f"Working on #{job_num} - {stem}")
                    elif kind == "done":
                        self.status_label.configure(text="Done")
                        self.start_button.configure(state="normal")
                        if self._total_jobs > 0:
                            self.progress_bar["value"] = 100
                            self.progress_label.configure(
                                text=f"{self._total_jobs} / {self._total_jobs}  (100%)"
                            )
                        results, reports = payload
                        summary = summarize_results(results)
                        self._append_log(f"\nReports created: {reports}\n")
                        self._schedule_modal(
                            lambda text=summary.alert_text: messagebox.showinfo("Conversion Complete", text)
                        )
                        break
                    elif kind == "error":
                        self.status_label.configure(text="Failed")
                        self.start_button.configure(state="normal")
                        self._schedule_modal(lambda error=payload: messagebox.showerror("Conversion failed", str(error)))
                        break
        except queue.Empty:
            pass
        if pending_log_lines:
            self._append_log("".join(pending_log_lines))
        self._schedule_poll()

    def _append_log(self, text: str) -> None:
        self.log_box.insert("end", text)
        self.log_box.see("end")

    def _bring_to_front(self) -> None:
        # On macOS, Tkinter windows don't automatically become the key/active
        # window on launch. The first click is consumed by the OS to focus the
        # window rather than being delivered to the widget. Force the window
        # frontmost so the first click reaches the widget directly.
        self.update_idletasks()
        if sys.platform == "darwin":
            try:
                from subprocess import run as _run
                _run(
                    [
                        "osascript", "-e",
                        f'tell app "System Events" to set frontmost of '
                        f'the first process whose unix id is {os.getpid()} to true',
                    ],
                    check=False,
                    capture_output=True,
                )
            except Exception:
                pass
        self.lift()
        self.attributes("-topmost", True)
        self.after(150, lambda: None if self._is_closing else self.attributes("-topmost", False))
        self.focus_force()

    def _schedule_poll(self) -> None:
        if not self._is_closing:
            active = self.worker is not None and self.worker.is_alive()
            interval = 100 if active else 500
            self._poll_after_id = self.after(interval, self._poll_queue)

    def _schedule_modal(self, callback: Callable[[], None]) -> None:
        after_id = ""

        def run() -> None:
            if after_id in self._modal_after_ids:
                self._modal_after_ids.remove(after_id)
            if not self._is_closing:
                callback()

        after_id = self.after(0, run)
        self._modal_after_ids.append(after_id)

    def _on_close(self) -> None:
        self._is_closing = True
        if self._poll_after_id:
            try:
                self.after_cancel(self._poll_after_id)
            except tk.TclError:
                pass
        for after_id in self._modal_after_ids:
            try:
                self.after_cancel(after_id)
            except tk.TclError:
                pass
        self._modal_after_ids.clear()
        self.destroy()


def main() -> None:
    app = ConverterApp()
    app.mainloop()


if __name__ == "__main__":
    main()

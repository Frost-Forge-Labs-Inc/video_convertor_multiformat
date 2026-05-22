"""Core media conversion workflow for Universal Media Converter.

Copyright 2026 Frost Forge Labs Inc.
https://frostforgelabs.ca
Licensed under the Apache License, Version 2.0.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
import time
from pathlib import Path
from typing import Callable

from .models import AUDIO_FORMATS, IMAGE_FORMATS, VIDEO_FORMATS, ConversionConfig, ConversionResult

LOGGER = logging.getLogger(__name__)
ProgressCallback = Callable[[ConversionResult], None]
StartCallback = Callable[[int, Path], None]


class MediaConverter:
    def __init__(self, ffmpeg_path: Path) -> None:
        self.ffmpeg_path = ffmpeg_path

    def discover_files(self, config: ConversionConfig) -> list[Path]:
        pattern = "**/*" if config.recursive else "*"
        files: list[Path] = []
        output_root = config.output_dir.resolve()

        for path in config.input_dir.glob(pattern):
            if not path.is_file() or path.name.startswith("."):
                continue
            try:
                resolved = path.resolve()
                if output_root == resolved or output_root in resolved.parents:
                    continue
            except OSError:
                pass
            if config.scan_all_files or path.suffix.lower() in config.supported_extensions:
                files.append(path)
        return sorted(files)

    def convert_directory(
        self,
        config: ConversionConfig,
        progress_callback: ProgressCallback | None = None,
        start_callback: StartCallback | None = None,
    ) -> list[ConversionResult]:
        self._validate_config(config)
        results: list[ConversionResult] = []
        files = self.discover_files(config)
        formats = config.normalized_output_formats()
        LOGGER.info("Discovered %d input file(s). Output formats: %s", len(files), ", ".join(formats))

        job_num = 0
        for source in files:
            for output_format in formats:
                job_num += 1
                if start_callback:
                    start_callback(job_num, source)
                result = self.process_file(source, output_format, config)
                results.append(result)
                LOGGER.info(
                    "%s | %s -> %s | %s",
                    result.status,
                    result.source,
                    result.destination,
                    result.message,
                )
                if progress_callback:
                    progress_callback(result)

        return results

    def process_file(self, source: Path, output_format: str, config: ConversionConfig) -> ConversionResult:
        start = time.perf_counter()
        fmt = output_format.strip().lower().lstrip(".")
        destination = self._destination_for(source, fmt, config)
        destination.parent.mkdir(parents=True, exist_ok=True)

        if destination.exists() and not config.overwrite:
            return ConversionResult(
                source=source,
                destination=destination,
                status="skipped",
                action="skipped",
                output_format=fmt,
                message="Destination exists. Use overwrite to replace it.",
                duration_seconds=time.perf_counter() - start,
            )

        try:
            source_fmt = source.suffix.lower().lstrip(".")
            should_copy = config.copy_same_extension or (config.copy_mp4 and fmt == "mp4" and source_fmt == "mp4")
            if should_copy and source_fmt == fmt:
                shutil.copy2(source, destination)
                return ConversionResult(
                    source=source,
                    destination=destination,
                    status="success",
                    action="copied",
                    output_format=fmt,
                    message=f".{fmt} copied without re-encoding.",
                    duration_seconds=time.perf_counter() - start,
                )

            # For cross-container video conversions, attempt stream copy (remux) before
            # committing to a full re-encode. H.264 in MKV → MP4 remuxes in seconds;
            # incompatible codecs (VP9 → MP4) fail fast and fall through to re-encode.
            if fmt in VIDEO_FORMATS and source_fmt != fmt:
                remux = self._try_stream_copy(source, destination, fmt, config, start)
                if remux is not None:
                    return remux

            cmd = self._build_ffmpeg_command(source, destination, fmt, config)
            LOGGER.debug("Running command: %s", " ".join(cmd))
            completed = subprocess.run(cmd, capture_output=True, text=True, check=False)

            if completed.returncode != 0:
                error_text = (completed.stderr or completed.stdout or "Unknown FFmpeg error").strip()
                return ConversionResult(
                    source=source,
                    destination=destination,
                    status="failed",
                    action="failed",
                    output_format=fmt,
                    message=error_text[-1500:],
                    duration_seconds=time.perf_counter() - start,
                    ffmpeg_return_code=completed.returncode,
                )

            return ConversionResult(
                source=source,
                destination=destination,
                status="success",
                action="converted",
                output_format=fmt,
                message=f"Converted to .{fmt}.",
                duration_seconds=time.perf_counter() - start,
                ffmpeg_return_code=completed.returncode,
            )
        except Exception as exc:  # guardrail for batch runs
            LOGGER.exception("Unexpected failure while processing %s", source)
            return ConversionResult(
                source=source,
                destination=destination,
                status="failed",
                action="failed",
                output_format=fmt,
                message=str(exc),
                duration_seconds=time.perf_counter() - start,
            )

    def _destination_for(self, source: Path, output_format: str, config: ConversionConfig) -> Path:
        if config.preserve_structure:
            relative = source.relative_to(config.input_dir)
        else:
            relative = Path(source.name)
        # Per-format root keeps outputs separated: output/mp3/playlist/p_a/file.mp3
        return (config.output_dir / output_format / relative).with_suffix(f".{output_format}")

    def _build_ffmpeg_command(self, source: Path, destination: Path, output_format: str, config: ConversionConfig) -> list[str]:
        cmd = [str(self.ffmpeg_path), "-hide_banner"]
        cmd.append("-y" if config.overwrite else "-n")
        cmd += ["-i", str(source), "-map_metadata", "0"]

        if output_format in AUDIO_FORMATS:
            cmd += self._audio_args(output_format, config)
        elif output_format in IMAGE_FORMATS:
            cmd += self._image_args(output_format)
        else:
            cmd += self._video_args(output_format, config)

        cmd.append(str(destination))
        return cmd

    def _try_stream_copy(
        self,
        source: Path,
        destination: Path,
        fmt: str,
        config: ConversionConfig,
        start: float,
    ) -> ConversionResult | None:
        """Attempt to remux streams without re-encoding. Returns a result on success, None if the
        source codecs are incompatible with the target container (caller should re-encode instead)."""
        cmd = [
            str(self.ffmpeg_path), "-hide_banner",
            "-y" if config.overwrite else "-n",
            "-i", str(source),
            "-map_metadata", "0",
            "-map", "0:v:0?",
            "-map", "0:a?",
            "-c", "copy",
        ]
        if fmt in {"mp4", "m4v", "mov"}:
            cmd += ["-movflags", "+faststart"]
        cmd.append(str(destination))

        completed = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if completed.returncode == 0:
            return ConversionResult(
                source=source,
                destination=destination,
                status="success",
                action="remuxed",
                output_format=fmt,
                message=f"Remuxed to .{fmt} without re-encoding.",
                duration_seconds=time.perf_counter() - start,
                ffmpeg_return_code=0,
            )
        # Clean up any partial output left by the failed attempt before re-encoding.
        try:
            if destination.exists():
                destination.unlink()
        except OSError:
            pass
        return None

    def _video_args(self, output_format: str, config: ConversionConfig) -> list[str]:
        args = ["-map", "0:v:0?", "-map", "0:a?"]
        if output_format == "webm":
            args += ["-c:v", "libvpx-vp9", "-crf", str(config.crf), "-b:v", "0", "-c:a", "libopus", "-b:a", config.audio_bitrate]
        elif output_format == "avi":
            args += ["-c:v", "mpeg4", "-q:v", "2", "-c:a", "mp3", "-b:a", config.audio_bitrate]
        else:
            args += [
                "-c:v", "libx264",
                "-preset", config.preset,
                "-crf", str(config.crf),
                "-pix_fmt", "yuv420p",
                "-c:a", "aac",
                "-b:a", config.audio_bitrate,
            ]
            if output_format in {"mp4", "m4v", "mov"}:
                args += ["-movflags", "+faststart"]
        return args

    def _audio_args(self, output_format: str, config: ConversionConfig) -> list[str]:
        args = ["-vn", "-map", "0:a:0?"]
        codec_by_format = {
            "mp3": ["-c:a", "libmp3lame", "-b:a", config.audio_bitrate],
            "aac": ["-c:a", "aac", "-b:a", config.audio_bitrate],
            "m4a": ["-c:a", "aac", "-b:a", config.audio_bitrate],
            "wav": ["-c:a", "pcm_s16le"],
            "flac": ["-c:a", "flac"],
            "ogg": ["-c:a", "libvorbis", "-q:a", "5"],
            "opus": ["-c:a", "libopus", "-b:a", config.audio_bitrate],
        }
        return args + codec_by_format.get(output_format, ["-c:a", "aac", "-b:a", config.audio_bitrate])

    def _image_args(self, output_format: str) -> list[str]:
        # Export one representative frame for image formats. GIF gets a short animated sample.
        if output_format == "gif":
            return ["-t", "8", "-vf", "fps=12,scale=720:-1:flags=lanczos"]
        if output_format in {"jpg", "jpeg"}:
            return ["-frames:v", "1", "-q:v", "2"]
        return ["-frames:v", "1"]

    @staticmethod
    def _validate_config(config: ConversionConfig) -> None:
        if not config.input_dir.exists() or not config.input_dir.is_dir():
            raise ValueError(f"Input directory does not exist: {config.input_dir}")
        if config.input_dir.resolve() == config.output_dir.resolve():
            raise ValueError("Input and output directories must be different.")
        if not 0 <= config.crf <= 51:
            raise ValueError("CRF must be between 0 and 51. Lower means better quality/larger files.")
        if not config.normalized_output_formats():
            raise ValueError("At least one output format is required.")


# Backwards-compatible class name for older imports.
VideoConverter = MediaConverter

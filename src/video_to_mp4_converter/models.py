from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Literal

Status = Literal["success", "failed", "skipped"]
Action = Literal["converted", "copied", "skipped", "failed"]

DEFAULT_OUTPUT_FORMATS = ("mp4",)
DEFAULT_INPUT_EXTENSIONS = (
    # video
    ".avi", ".mov", ".mkv", ".wmv", ".flv", ".webm", ".m4v", ".mpg", ".mpeg",
    ".3gp", ".ts", ".mts", ".m2ts", ".vob", ".ogv", ".mp4",
    # audio
    ".mp3", ".wav", ".aac", ".m4a", ".flac", ".ogg", ".opus", ".wma", ".aiff",
    # common image inputs supported by FFmpeg
    ".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp", ".gif",
)

VIDEO_FORMATS = {"mp4", "mkv", "mov", "webm", "avi", "m4v"}
AUDIO_FORMATS = {"mp3", "aac", "m4a", "wav", "flac", "ogg", "opus"}
IMAGE_FORMATS = {"jpg", "jpeg", "png", "webp", "gif"}


@dataclass(frozen=True)
class ConversionConfig:
    input_dir: Path
    output_dir: Path
    recursive: bool = True
    overwrite: bool = False
    crf: int = 18
    preset: str = "slow"
    audio_bitrate: str = "192k"
    preserve_structure: bool = True
    copy_same_extension: bool = True
    copy_mp4: bool = True  # backwards-compatible alias for older callers
    output_formats: tuple[str, ...] = DEFAULT_OUTPUT_FORMATS
    supported_extensions: tuple[str, ...] = DEFAULT_INPUT_EXTENSIONS
    scan_all_files: bool = False

    def normalized_output_formats(self) -> tuple[str, ...]:
        cleaned: list[str] = []
        for item in self.output_formats:
            fmt = item.strip().lower().lstrip(".")
            if fmt and fmt not in cleaned:
                cleaned.append(fmt)
        return tuple(cleaned or DEFAULT_OUTPUT_FORMATS)


@dataclass
class ConversionResult:
    source: Path
    destination: Path | None
    status: Status
    action: Action
    output_format: str = ""
    message: str = ""
    duration_seconds: float = 0.0
    started_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    ffmpeg_return_code: int | None = None

    def as_dict(self) -> dict[str, object]:
        return {
            "source": str(self.source),
            "destination": str(self.destination) if self.destination else "",
            "output_format": self.output_format,
            "status": self.status,
            "action": self.action,
            "message": self.message,
            "duration_seconds": round(self.duration_seconds, 3),
            "started_at": self.started_at,
            "ffmpeg_return_code": self.ffmpeg_return_code if self.ffmpeg_return_code is not None else "",
        }

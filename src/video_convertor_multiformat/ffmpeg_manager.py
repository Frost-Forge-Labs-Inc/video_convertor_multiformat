"""FFmpeg discovery and local preparation helpers.

Copyright 2026 Frost Forge Labs Inc.
https://frostforgelabs.ca
Licensed under the Apache License, Version 2.0.
"""

from __future__ import annotations

import logging
import os
import shutil
import stat
import subprocess
from pathlib import Path

LOGGER = logging.getLogger(__name__)


class FFmpegNotFoundError(RuntimeError):
    pass


class FFmpegManager:
    """Finds or prepares an FFmpeg executable.

    Priority:
    1. Explicit path passed by the user.
    2. Local project tools directory.
    3. System PATH.
    4. imageio-ffmpeg package binary copied into tools directory.
    """

    def __init__(self, tools_dir: Path | None = None, explicit_path: Path | None = None) -> None:
        self.tools_dir = tools_dir or Path(__file__).resolve().parents[3] / "tools"
        self.explicit_path = explicit_path

    def get_ffmpeg_path(self, auto_prepare: bool = True) -> Path:
        candidates: list[Path] = []
        if self.explicit_path:
            candidates.append(self.explicit_path)

        local_name = "ffmpeg.exe" if os.name == "nt" else "ffmpeg"
        candidates.append(self.tools_dir / local_name)

        system_ffmpeg = shutil.which("ffmpeg")
        if system_ffmpeg:
            candidates.append(Path(system_ffmpeg))

        for candidate in candidates:
            if candidate.exists() and self._is_executable(candidate):
                LOGGER.info("Using FFmpeg executable: %s", candidate)
                return candidate

        if auto_prepare:
            return self.prepare_local_ffmpeg()

        raise FFmpegNotFoundError("FFmpeg executable was not found.")

    def prepare_local_ffmpeg(self) -> Path:
        """Prepare local FFmpeg by copying imageio-ffmpeg's binary into ./tools.

        This avoids hard-coded third-party download URLs and works on macOS, Windows,
        and Linux as long as imageio-ffmpeg supports the current Python platform.
        """
        try:
            import imageio_ffmpeg
        except ImportError as exc:
            raise FFmpegNotFoundError(
                "FFmpeg not found and imageio-ffmpeg is not installed. Run: pip install imageio-ffmpeg"
            ) from exc

        source = Path(imageio_ffmpeg.get_ffmpeg_exe())
        if not source.exists():
            raise FFmpegNotFoundError("imageio-ffmpeg did not provide a valid FFmpeg binary.")

        self.tools_dir.mkdir(parents=True, exist_ok=True)
        dest = self.tools_dir / ("ffmpeg.exe" if os.name == "nt" else "ffmpeg")
        shutil.copy2(source, dest)
        self._make_executable(dest)
        LOGGER.info("Prepared local FFmpeg: %s", dest)
        return dest

    def version(self, ffmpeg_path: Path | None = None) -> str:
        path = ffmpeg_path or self.get_ffmpeg_path()
        completed = subprocess.run(
            [str(path), "-version"],
            capture_output=True,
            text=True,
            check=False,
        )
        first_line = completed.stdout.splitlines()[0] if completed.stdout else "Unknown FFmpeg version"
        return first_line

    @staticmethod
    def _make_executable(path: Path) -> None:
        if os.name != "nt":
            path.chmod(path.stat().st_mode | stat.S_IEXEC)

    @staticmethod
    def _is_executable(path: Path) -> bool:
        return path.is_file() and (os.access(path, os.X_OK) or os.name == "nt")

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .converter import MediaConverter
from .ffmpeg_manager import FFmpegManager
from .logging_setup import setup_logging
from .models import ConversionConfig
from .reporting import write_reports


def parse_formats(value: str) -> tuple[str, ...]:
    return tuple(part.strip().lower().lstrip(".") for part in value.split(",") if part.strip())


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Batch convert media files into one or more output formats.")
    parser.add_argument("--input", "-i", required=True, type=Path, help="Input directory containing media files.")
    parser.add_argument("--output", "-o", required=True, type=Path, help="Output root directory.")
    parser.add_argument("--formats", "-f", default="mp4", help="Comma-separated output formats. Example: mp4,mp3,wav")
    parser.add_argument("--ffmpeg", type=Path, default=None, help="Optional explicit FFmpeg executable path.")
    parser.add_argument("--no-recursive", action="store_true", help="Only process files directly in input directory.")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing output files.")
    parser.add_argument("--crf", type=int, default=18, help="Video quality, 0-51. Lower is better. Default: 18.")
    parser.add_argument("--preset", default="slow", help="FFmpeg x264 preset. Default: slow.")
    parser.add_argument("--audio-bitrate", default="192k", help="Audio bitrate. Default: 192k.")
    parser.add_argument("--flat", action="store_true", help="Do not preserve input subfolder structure.")
    parser.add_argument("--convert-same-extension", action="store_true", help="Re-encode files even when input and output extensions match.")
    parser.add_argument("--all-files", action="store_true", help="Attempt every file, not just common media extensions.")
    parser.add_argument("--prepare-ffmpeg", action="store_true", help="Prepare local FFmpeg in ./tools and exit.")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose console logs.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    log_file = setup_logging(args.output / "logs", verbose=args.verbose)

    manager = FFmpegManager(explicit_path=args.ffmpeg)
    try:
        if args.prepare_ffmpeg:
            path = manager.prepare_local_ffmpeg()
            print(f"Prepared FFmpeg: {path}")
            return 0

        ffmpeg_path = manager.get_ffmpeg_path(auto_prepare=True)
        print(manager.version(ffmpeg_path))

        config = ConversionConfig(
            input_dir=args.input,
            output_dir=args.output,
            recursive=not args.no_recursive,
            overwrite=args.overwrite,
            crf=args.crf,
            preset=args.preset,
            audio_bitrate=args.audio_bitrate,
            preserve_structure=not args.flat,
            copy_same_extension=not args.convert_same_extension,
            output_formats=parse_formats(args.formats),
            scan_all_files=args.all_files,
        )
        results = MediaConverter(ffmpeg_path).convert_directory(config)
        csv_path, json_path, summary_path = write_reports(results, args.output / "reports")

        failed = sum(1 for result in results if result.status == "failed")
        print(f"\nDone. Log: {log_file}")
        print(f"Reports: {csv_path}, {json_path}, {summary_path}")
        return 2 if failed else 0
    except Exception as exc:
        print(f"Fatal error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

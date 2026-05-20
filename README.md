# Universal Media Converter

A cross-platform Python project for batch converting media files into one or more output formats, with:

- CLI (Command Line Interface) and Tkinter desktop UI
- macOS, Windows, and Linux support
- automatic FFmpeg discovery/preparation
- multi-select output formats such as `mp4`, `mp3`, `wav`, `mkv`, `webm`, `flac`
- recursive subfolder scanning
- mirrored input folder structure in each output format directory
- structured logs
- CSV, JSON, and Markdown result reports
- success/failure tracking per conversion job
- direct copy for files already matching the requested output format
- free and open source under the Apache License 2.0

Created and maintained by [Frost Forge Labs Inc.](https://frostforgelabs.ca).

## Output Folder Design

If the input contains:

```text
input/
  playlist/
    p_a/
      song.mov
      talk.mp4
```

and you select `mp4,mp3,wav`, the output is organized like this:

```text
output/
  mp4/
    playlist/
      p_a/
        song.mp4
        talk.mp4
  mp3/
    playlist/
      p_a/
        song.mp3
        talk.mp3
  wav/
    playlist/
      p_a/
        song.wav
        talk.wav
  logs/
    media-convert.log
  reports/
    conversion_report_YYYYMMDD_HHMMSS.csv
    conversion_report_YYYYMMDD_HHMMSS.json
    conversion_summary_YYYYMMDD_HHMMSS.md
```

So each output format gets its own clean little kingdom. No filename soup. 🗂️

## Why FFmpeg?

FFmpeg is a mature cross-platform tool for recording, converting, and streaming audio/video. This project uses FFmpeg underneath Python rather than trying to reimplement codecs.

## License and Support

Universal Media Converter is free and open source under the Apache License 2.0.

Copyright 2026 Frost Forge Labs Inc. See [frostforgelabs.ca](https://frostforgelabs.ca).

If this project saves you time, you can support development through the funding links exposed by GitHub Sponsors for this repository.

## FFmpeg Strategy

FFmpeg does not provide one universal official binary for every operating system. The official download page points users to OS/package-specific builds. To keep this project stable and GitHub-friendly, the code uses this priority order:

1. Use an explicit FFmpeg path if provided.
2. Use `./tools/ffmpeg` or `./tools/ffmpeg.exe` if already prepared.
3. Use `ffmpeg` from the system `PATH`.
4. Use `imageio-ffmpeg` and copy its bundled binary into `./tools`.

`imageio-ffmpeg` publishes platform-specific wheels containing FFmpeg binaries for supported platforms, which avoids fragile direct download URLs.

## Install From GitHub

```bash
git clone https://github.com/Frost-Forge-Labs-Inc/video_convertor_multiformat.git
cd video_convertor_multiformat
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -e .
```

Windows PowerShell:

```powershell
git clone https://github.com/Frost-Forge-Labs-Inc/video_convertor_multiformat.git
cd video_convertor_multiformat
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install -U pip
py -m pip install -e .
```

Repository name: `video_convertor_multiformat`.

Python package/module name: `video_convertor_multiformat`.

Python distribution/package name: `video-convertor-multiformat`.

Installed commands: `media-convert` and `media-convert-ui`.

## Update, Uninstall, Or Reinstall

If you installed from a cloned GitHub checkout with `pip install -e .`, update it
from inside the repository. Activate the same virtual environment you used for
installation before running the `pip` commands.

```bash
cd video_convertor_multiformat
git pull
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -e .
```

Windows PowerShell:

```powershell
cd video_convertor_multiformat
git pull
.\.venv\Scripts\Activate.ps1
py -m pip install -U pip
py -m pip install -e .
```

To uninstall the command-line tools from the active Python environment:

```bash
python -m pip uninstall video-convertor-multiformat
```

`pip uninstall` removes the installed commands, but it does not delete the cloned
repository, local reports, prepared FFmpeg tools, or other local files.

To fully remove a local editable install, uninstall it first, then delete the cloned
folder. This permanently deletes local changes and generated files inside that
folder.

```bash
python -m pip uninstall video-convertor-multiformat
cd ..
rm -rf video_convertor_multiformat
```

Windows PowerShell:

```powershell
py -m pip uninstall video-convertor-multiformat
cd ..
Remove-Item -Recurse -Force .\video_convertor_multiformat
```

To reinstall a fresh copy, repeat the [Install From GitHub](#install-from-github)
steps.

## CLI Usage

Convert to MP4:

```bash
media-convert --input "/path/to/media" --output "/path/to/output"
```

Convert to multiple formats:

```bash
media-convert \
  --input "/Users/you/Media/raw" \
  --output "/Users/you/Media/converted" \
  --formats mp4,mp3,wav \
  --recursive \
  --crf 18 \
  --preset slow \
  --audio-bitrate 192k \
  --verbose
```

Legacy command names still work for compatibility:

```bash
video2mp4 --input ./input --output ./output --formats mp4,mp3
```

Or from inside the cloned repository before installing the package:

```bash
PYTHONPATH=src python3 -m video_convertor_multiformat.cli --input ./input --output ./output --formats mp4,mp3,wav
```

## Common Options

| Option | Purpose |
|---|---|
| `--formats mp4,mp3,wav` | Output to one or more formats |
| `--no-recursive` | Only scan the top-level input folder |
| `--flat` | Do not preserve subfolder structure |
| `--overwrite` | Replace existing output files |
| `--convert-same-extension` | Re-encode even when input and output formats match |
| `--all-files` | Attempt every file, not only common media extensions |
| `--prepare-ffmpeg` | Copy bundled FFmpeg into `./tools` and exit |

## Tkinter UI

```bash
media-convert-ui
```

Or:

```bash
python3 -m video_convertor_multiformat.ui_tkinter
```

The UI lets you choose input/output folders, select multiple output formats, scan subfolders, preserve folder structure, choose quality settings, and watch progress.

## Quality Settings

For MP4/MOV/MKV style outputs, the default uses high-quality H.264 settings:

```text
-c:v libx264 -preset slow -crf 18 -pix_fmt yuv420p -c:a aac -b:a 192k
```

Recommended CRF values:

| CRF | Meaning |
|---:|---|
| 16-18 | visually high quality, larger files |
| 19-23 | balanced quality and size |
| 24+ | smaller files, visible quality loss more likely |

Lower CRF means better quality and larger file size.

## Supported Output Formats

Built-in handling is included for:

- Video: `mp4`, `mkv`, `mov`, `webm`, `avi`, `m4v`
- Audio: `mp3`, `aac`, `m4a`, `wav`, `flac`, `ogg`, `opus`
- Image/frame export: `jpg`, `jpeg`, `png`, `webp`, `gif`

You can also enter custom FFmpeg-supported extensions. Unknown formats fall back to the default H.264/AAC-style video command.

## Existing MP4 and Same-Format Files

By default, files are copied directly when the source extension already matches the requested output extension. For example:

- `movie.mp4` -> `output/mp4/movie.mp4` is copied without re-encoding.
- `song.mp3` -> `output/mp3/song.mp3` is copied without re-encoding.

This avoids unnecessary quality loss and saves time.

To force re-encoding:

```bash
media-convert --input ./input --output ./output --formats mp4,mp3 --convert-same-extension
```

## Reports

Every run creates:

- CSV report for spreadsheet review
- JSON report for automation
- Markdown summary for humans

Each row includes source path, destination path, output format, status, action, error message, duration, and FFmpeg return code.

## macOS Notes

Option A, easiest:

```bash
pip install imageio-ffmpeg
```

The script will prepare FFmpeg automatically if needed.

Option B, Homebrew:

```bash
brew install ffmpeg
```

Then the script will use the system FFmpeg.

## Windows Notes

```powershell
git clone https://github.com/Frost-Forge-Labs-Inc/video_convertor_multiformat.git
cd video_convertor_multiformat
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -e .
media-convert --input "C:\Videos\raw" --output "C:\Videos\converted" --formats mp4,mp3
```

The project will use `imageio-ffmpeg` if `ffmpeg.exe` is not on `PATH`.

## Linux Notes

Either install system FFmpeg:

```bash
sudo apt install ffmpeg
```

or rely on:

```bash
pip install imageio-ffmpeg
```

## Project Architecture

```text
video_convertor_multiformat/
  README.md
  pyproject.toml
  requirements.txt
  LICENSE
  NOTICE
src/video_convertor_multiformat/
  cli.py              # CLI entry point
  ui_tkinter.py       # desktop UI
  converter.py        # conversion workflow
  ffmpeg_manager.py   # FFmpeg discovery/preparation
  logging_setup.py    # rotating logs
  reporting.py        # CSV/JSON/Markdown reports
  models.py           # dataclasses and config objects
```

## Design Choices

- **Scalable structure:** conversion logic is separate from CLI and UI.
- **Many-to-many conversion:** one input can produce multiple output formats.
- **Per-format directory trees:** output paths stay predictable and easy to browse.
- **Safe batch processing:** each conversion job returns its own result, so one bad file does not stop the entire batch.
- **Quality-first defaults:** CRF 18 and `slow` preset maintain strong quality for H.264 output.
- **Same-format copy behavior:** avoids unnecessary re-encoding when the source already matches the requested output.
- **Reports:** both machine-readable JSON/CSV and human-readable Markdown summary are generated.

## Future Enhancements

- Add drag-and-drop UI support
- Add pause/resume queue
- Add parallel conversion workers
- Add profile presets such as “YouTube MP4”, “Podcast MP3”, “Archive FLAC”
- Add progress percentage parsing from FFmpeg output
- Add checksum verification after copy
- Add GitHub Actions CI (Continuous Integration)

## License

Apache License 2.0. See `LICENSE` and `NOTICE`.

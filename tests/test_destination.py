from pathlib import Path

from video_convertor_multiformat.converter import MediaConverter
from video_convertor_multiformat.models import ConversionConfig


def test_destination_preserves_structure_and_uses_format_root(tmp_path: Path) -> None:
    source_root = tmp_path / "input"
    source = source_root / "playlist" / "p_a" / "clip.mov"
    source.parent.mkdir(parents=True)
    source.write_text("fake")

    config = ConversionConfig(input_dir=source_root, output_dir=tmp_path / "output", output_formats=("mp3",))
    converter = MediaConverter(Path("ffmpeg"))

    destination = converter._destination_for(source, "mp3", config)

    assert destination == tmp_path / "output" / "mp3" / "playlist" / "p_a" / "clip.mp3"


def test_destination_can_be_flat(tmp_path: Path) -> None:
    source_root = tmp_path / "input"
    source = source_root / "playlist" / "p_a" / "clip.mov"
    source.parent.mkdir(parents=True)
    source.write_text("fake")

    config = ConversionConfig(
        input_dir=source_root,
        output_dir=tmp_path / "output",
        preserve_structure=False,
        output_formats=("wav",),
    )
    converter = MediaConverter(Path("ffmpeg"))

    destination = converter._destination_for(source, "wav", config)

    assert destination == tmp_path / "output" / "wav" / "clip.wav"


def test_formats_are_normalized_and_deduplicated(tmp_path: Path) -> None:
    config = ConversionConfig(
        input_dir=tmp_path / "in",
        output_dir=tmp_path / "out",
        output_formats=(".MP4", "mp3", "mp4", " wav "),
    )

    assert config.normalized_output_formats() == ("mp4", "mp3", "wav")

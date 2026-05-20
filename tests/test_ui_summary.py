from pathlib import Path

from video_convertor_multiformat.models import ConversionResult
from video_convertor_multiformat.reporting import summarize_results


def test_summarize_results_counts_completion_statuses() -> None:
    results = [
        ConversionResult(Path("a.mkv"), Path("out/a.mp4"), "success", "converted"),
        ConversionResult(Path("b.mkv"), Path("out/b.mp4"), "success", "copied"),
        ConversionResult(Path("c.mkv"), Path("out/c.mp4"), "failed", "failed"),
        ConversionResult(Path("d.mkv"), Path("out/d.mp4"), "skipped", "skipped"),
    ]

    summary = summarize_results(results)

    assert summary.total == 4
    assert summary.succeeded == 2
    assert summary.failed == 1
    assert summary.skipped == 1
    assert summary.converted == 1
    assert summary.copied == 1
    assert summary.alert_text == (
        "Total files processed: 4\n"
        "Total converted files: 1\n"
        "Success: 2/4\n"
        "Skipped: 1/4\n"
        "Failed: 1/4"
    )


def test_summarize_results_handles_empty_runs() -> None:
    summary = summarize_results([])

    assert summary.total == 0
    assert summary.succeeded == 0
    assert summary.failed == 0
    assert summary.skipped == 0
    assert summary.converted == 0
    assert summary.copied == 0
    assert summary.alert_text == (
        "Total files processed: 0\n"
        "Total converted files: 0\n"
        "Success: 0/0\n"
        "Skipped: 0/0\n"
        "Failed: 0/0"
    )

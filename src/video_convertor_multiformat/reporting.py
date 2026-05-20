from __future__ import annotations

import csv
import json
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .models import ConversionResult


@dataclass(frozen=True)
class ConversionSummary:
    total: int
    succeeded: int
    failed: int
    skipped: int
    converted: int
    copied: int

    @property
    def alert_text(self) -> str:
        return (
            f"Total files processed: {self.total}\n"
            f"Total converted files: {self.converted}\n"
            f"Success: {self.succeeded}/{self.total}\n"
            f"Skipped: {self.skipped}/{self.total}\n"
            f"Failed: {self.failed}/{self.total}"
        )


def summarize_results(results: list[ConversionResult]) -> ConversionSummary:
    statuses = Counter(result.status for result in results)
    actions = Counter(result.action for result in results)
    return ConversionSummary(
        total=len(results),
        succeeded=statuses.get("success", 0),
        failed=statuses.get("failed", 0),
        skipped=statuses.get("skipped", 0),
        converted=actions.get("converted", 0),
        copied=actions.get("copied", 0),
    )


def write_reports(results: list[ConversionResult], report_dir: Path) -> tuple[Path, Path, Path]:
    report_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = report_dir / f"conversion_report_{timestamp}.csv"
    json_path = report_dir / f"conversion_report_{timestamp}.json"
    summary_path = report_dir / f"conversion_summary_{timestamp}.md"

    rows = [result.as_dict() for result in results]
    fieldnames = list(rows[0].keys()) if rows else ["source", "destination", "output_format", "status", "action", "message"]

    with csv_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    with json_path.open("w", encoding="utf-8") as file:
        json.dump(rows, file, indent=2)

    summary = summarize_results(results)
    formats = Counter(result.output_format for result in results)
    with summary_path.open("w", encoding="utf-8") as file:
        file.write("# Media Conversion Summary\n\n")
        file.write(f"Generated: {datetime.now().isoformat(timespec='seconds')}\n\n")
        file.write("## Results\n\n")
        file.write(f"- Total conversion jobs: {summary.total}\n")
        file.write(f"- Successful: {summary.succeeded}\n")
        file.write(f"- Failed: {summary.failed}\n")
        file.write(f"- Skipped: {summary.skipped}\n")
        file.write(f"- Converted: {summary.converted}\n")
        file.write(f"- Copied same-format files: {summary.copied}\n\n")

        file.write("## Output Formats\n\n")
        for fmt, count in sorted(formats.items()):
            file.write(f"- `{fmt}`: {count}\n")
        file.write("\n")

        failures = [r for r in results if r.status == "failed"]
        if failures:
            file.write("## Failures\n\n")
            for failure in failures:
                file.write(f"- `{failure.source}` -> `{failure.output_format}`: {failure.message}\n")

    return csv_path, json_path, summary_path

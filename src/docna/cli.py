"""Optional CLI entry point."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from docna.config import Settings
from docna.service import DocNAService


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the DocNA pipeline on a DOCX file.")
    parser.add_argument("input", type=Path, help="Path to the input .docx file")
    args = parser.parse_args(argv)

    settings = Settings.from_env()
    service = DocNAService(settings)
    result = service.process_file(args.input)
    print(f"job_id={result.job_id} status={result.status}")
    if result.output_path:
        print(f"output={result.output_path}")
    if result.review_report_path:
        print(f"review={result.review_report_path}")
    return 0 if result.status == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())

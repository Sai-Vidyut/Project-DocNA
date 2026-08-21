"""Shared helpers for placement and apply tests."""

from __future__ import annotations

import hashlib
import shutil
import subprocess
import sys
from pathlib import Path

from docna.adapters.docx import DocxAdapter
from docna.adapters.docx.parse import parse as parse_docx
from docna.ir import Answer, DocumentIR, PlacementOp, Task

PLACEMENT_FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "docx"


def ensure_placement_fixture(name: str) -> Path:
    path = PLACEMENT_FIXTURE_DIR / name
    if not path.exists():
        subprocess.run(
            [sys.executable, str(PLACEMENT_FIXTURE_DIR / "generate_placement_fixtures.py")],
            check=True,
        )
    assert path.exists(), f"Missing placement fixture: {path}"
    return path


def parse_placement_fixture(name: str) -> DocumentIR:
    return parse_docx(ensure_placement_fixture(name))


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def working_copy(original: Path, work_dir: Path) -> Path:
    work_dir.mkdir(parents=True, exist_ok=True)
    copy_path = work_dir / original.name
    shutil.copy2(original, copy_path)
    return copy_path


def apply_ops(original: Path, ops: list[PlacementOp], work_dir: Path) -> Path:
    adapter = DocxAdapter()
    copy_path = working_copy(original, work_dir)
    return adapter.apply(copy_path, ops)


def answer_for(task_id: str, text: str) -> Answer:
    return Answer(task_id=task_id, text=text, confidence=0.95)

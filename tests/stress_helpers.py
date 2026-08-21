"""Helpers for Phase 12 stress-test DOCX fixtures."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

STRESS_DIR = Path(__file__).resolve().parent / "fixtures" / "docx" / "stress"
GENERATOR = STRESS_DIR.parent / "generate_stress_fixtures.py"


def ensure_stress_fixture(name: str) -> Path:
    path = STRESS_DIR / name
    if not path.exists():
        subprocess.run([sys.executable, str(GENERATOR)], check=True)
    assert path.exists(), f"Missing stress fixture: {path}"
    return path


def ensure_all_stress_fixtures() -> list[Path]:
    if not STRESS_DIR.exists() or not any(STRESS_DIR.glob("*.docx")):
        subprocess.run([sys.executable, str(GENERATOR)], check=True)
    return sorted(STRESS_DIR.glob("*.docx"))

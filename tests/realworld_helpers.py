"""Helpers for real-world validation fixtures."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REALWORLD_DIR = Path(__file__).resolve().parent / "fixtures" / "docx" / "realworld"
GENERATOR = REALWORLD_DIR.parent / "generate_realworld_fixtures.py"


def ensure_realworld_fixture(name: str) -> Path:
    path = REALWORLD_DIR / name
    if not path.exists():
        subprocess.run([sys.executable, str(GENERATOR)], check=True)
    assert path.exists(), f"Missing real-world fixture: {path}"
    return path


def ensure_all_realworld_fixtures() -> list[Path]:
    if not REALWORLD_DIR.exists() or not any(REALWORLD_DIR.glob("*.docx")):
        subprocess.run([sys.executable, str(GENERATOR)], check=True)
    return sorted(REALWORLD_DIR.glob("*.docx"))

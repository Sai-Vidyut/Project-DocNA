"""Shared pytest fixtures for DocNA tests."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
WEB_DIST = ROOT / "web" / "dist"
WEB_SRC = ROOT / "web" / "src"


def _ensure_frontend_built() -> None:
    if (WEB_DIST / "index.html").exists():
        return
    subprocess.run(["npm", "run", "build"], cwd=ROOT / "web", check=True)


@pytest.fixture(scope="session", autouse=True)
def build_frontend() -> None:
    _ensure_frontend_built()


def frontend_source_text() -> str:
    chunks: list[str] = []
    for pattern in ("*.tsx", "*.ts"):
        for path in WEB_SRC.rglob(pattern):
            if "node_modules" in path.parts:
                continue
            chunks.append(path.read_text(encoding="utf-8"))
    return "\n".join(chunks)


def homepage_text(client) -> str:
    response = client.get("/")
    html = response.text
    import re

    match = re.search(r'src="(/assets/[^"]+\.js)"', html)
    if match:
        bundle = client.get(match.group(1))
        if bundle.status_code == 200:
            return html + bundle.text
    return html

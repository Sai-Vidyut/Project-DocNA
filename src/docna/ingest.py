"""Upload validation for supported source formats.

This module is outside the core isolation boundary and may use zipfile.
"""

from __future__ import annotations

import zipfile
from pathlib import Path

ACCEPTED_EXTENSIONS = frozenset({".docx"})
REJECTED_EXTENSIONS = frozenset({".doc", ".docm", ".pdf", ".txt", ".md", ".pptx"})
DOCX_REQUIRED_PARTS = frozenset({"[Content_Types].xml", "word/document.xml"})
MACRO_PARTS = frozenset({"word/vbaProject.bin", "word/vbaData.xml"})
ENCRYPTION_PARTS = frozenset(
    {"EncryptionInfo", "EncryptedPackage", "word/document.xml.enc"}
)


class ValidationError(Exception):
    """Raised when an uploaded file fails validation."""


def validate_upload(path: Path, *, max_file_size: int) -> str:
    """Validate an uploaded file and return the resolved source format.

  Raises ``ValidationError`` for unsupported, oversized, corrupt, encrypted,
  or macro-enabled files.
    """
    if not path.exists():
        raise ValidationError("File does not exist")

    suffix = path.suffix.lower()
    if suffix in REJECTED_EXTENSIONS:
        raise ValidationError(f"Unsupported file type: {suffix}")
    if suffix not in ACCEPTED_EXTENSIONS:
        raise ValidationError(
            f"Unsupported file type: {suffix or '(none)'}. Only .docx is accepted."
        )

    size = path.stat().st_size
    if size == 0:
        raise ValidationError("File is empty")
    if size > max_file_size:
        raise ValidationError(
            f"File exceeds maximum size of {max_file_size} bytes"
        )

    _validate_docx_package(path)
    return "docx"


def _validate_docx_package(path: Path) -> None:
    if not zipfile.is_zipfile(path):
        raise ValidationError("File is not a valid DOCX package")

    try:
        with zipfile.ZipFile(path, "r") as archive:
            names = set(archive.namelist())
    except zipfile.BadZipFile as exc:
        raise ValidationError("DOCX package is corrupt or unreadable") from exc

    if not DOCX_REQUIRED_PARTS.issubset(names):
        raise ValidationError("DOCX package is missing required parts")

    if names & ENCRYPTION_PARTS:
        raise ValidationError("Encrypted DOCX files are not supported")

    if names & MACRO_PARTS:
        raise ValidationError("Macro-enabled DOCX files are not supported")

    try:
        with zipfile.ZipFile(path, "r") as archive:
            archive.read("word/document.xml")
    except (KeyError, zipfile.BadZipFile, RuntimeError) as exc:
        raise ValidationError("DOCX package is corrupt or unreadable") from exc

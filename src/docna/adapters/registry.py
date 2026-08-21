"""Map source format names to adapter classes.

This module only resolves adapters. It must not parse files, plan placements,
or call an AI provider.
"""

from docna.adapters.base import FormatAdapter, UnsupportedFormatError
from docna.adapters.docx import DocxAdapter
from docna.adapters.md import MarkdownAdapter
from docna.adapters.pdf import PdfAdapter
from docna.adapters.pptx import PptxAdapter
from docna.adapters.txt import TxtAdapter
from docna.ir import SOURCE_FORMATS

_ADAPTERS: dict[str, type[FormatAdapter]] = {
    "docx": DocxAdapter,
    "pdf": PdfAdapter,
    "txt": TxtAdapter,
    "md": MarkdownAdapter,
    "pptx": PptxAdapter,
}

if set(_ADAPTERS) != set(SOURCE_FORMATS):
    raise RuntimeError("Adapter registry is out of sync with SourceFormat")


def registered_formats() -> frozenset[str]:
    """Return the format names the registry knows about."""
    return frozenset(_ADAPTERS)


def get_adapter(source_format: str) -> FormatAdapter:
    """Return a new adapter instance for ``source_format``.

    Unknown names raise ``UnsupportedFormatError``. Registered formats that
    are not yet implemented still resolve here; their ``parse`` / ``apply``
    methods raise ``NotImplementedError``.
    """
    adapter_cls = _ADAPTERS.get(source_format)
    if adapter_cls is None:
        known = ", ".join(sorted(SOURCE_FORMATS))
        raise UnsupportedFormatError(
            f"Unsupported source format: {source_format!r}. Known formats: {known}."
        )
    return adapter_cls()

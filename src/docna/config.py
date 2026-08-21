"""Centralized application configuration from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from docna.ai.providers.spec import ProviderSpec

SUPPORTED_AI_PROVIDERS = frozenset(
    {"mock", "gemini", "cerebras", "groq", "huggingface", "openrouter", "openai"}
)

DEFAULT_FALLBACK_ORDER: tuple[str, ...] = (
    "cerebras",
    "groq",
    "huggingface",
    "openrouter",
)

_PROVIDER_DEFINITIONS: dict[str, tuple[str, str, str | None]] = {
    "gemini": ("GEMINI_API_KEY", "GEMINI_MODEL", None),
    "cerebras": ("CEREBRAS_API_KEY", "CEREBRAS_MODEL", "https://api.cerebras.ai/v1"),
    "groq": ("GROQ_API_KEY", "GROQ_MODEL", "https://api.groq.com/openai/v1"),
    "huggingface": ("HF_TOKEN", "HF_MODEL", "https://router.huggingface.co/v1"),
    "openrouter": ("OPENROUTER_API_KEY", "OPENROUTER_MODEL", "https://openrouter.ai/api/v1"),
    "openai": ("OPENAI_API_KEY", "OPENAI_MODEL", None),
}


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    return int(raw)


def _env_path(name: str, default: Path) -> Path:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    return Path(raw).expanduser()


def _env_str(*names: str, default: str | None = None) -> str | None:
    for name in names:
        raw = os.environ.get(name)
        if raw is not None and raw.strip() != "":
            return raw.strip()
    return default


def load_dotenv_local(path: Path | None = None) -> None:
    """Load ``.env.local`` without overwriting existing environment variables."""
    env_path = path or (Path.cwd() / ".env.local")
    if not env_path.exists():
        return

    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("export "):
            stripped = stripped[len("export ") :].strip()
        if "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        key = key.strip()
        value = value.strip()
        if not key:
            continue
        if (value.startswith('"') and value.endswith('"')) or (
            value.startswith("'") and value.endswith("'")
        ):
            value = value[1:-1]
        if key not in os.environ:
            os.environ[key] = value


def parse_provider_spec(name: str) -> ProviderSpec | None:
    """Return a configured provider spec, or ``None`` if credentials are incomplete."""
    provider_name = name.lower()
    definition = _PROVIDER_DEFINITIONS.get(provider_name)
    if definition is None:
        return None

    key_env, model_env, default_base_url = definition
    api_key = _env_str(key_env)
    model = _env_str(model_env)
    if not api_key or not model:
        return None

    return ProviderSpec(
        name=provider_name,
        api_key=api_key,
        model=model,
        base_url=default_base_url,
    )


def parse_fallback_order() -> tuple[str, ...]:
    """Return configured fallback provider order."""
    raw = _env_str("DOCNA_AI_FALLBACK_PROVIDERS", "AI_FALLBACK_PROVIDERS")
    if raw:
        return tuple(item.strip().lower() for item in raw.split(",") if item.strip())
    return DEFAULT_FALLBACK_ORDER


def parse_provider_chain(primary: str) -> tuple[ProviderSpec, ...]:
    """Build ordered provider chain: primary first, then configured fallbacks."""
    provider_name = primary.lower()
    if provider_name == "mock":
        return ()

    chain: list[ProviderSpec] = []
    seen: set[str] = set()

    primary_spec = parse_provider_spec(provider_name)
    if primary_spec is not None:
        chain.append(primary_spec)
        seen.add(primary_spec.name)

    for fallback_name in parse_fallback_order():
        if fallback_name in seen:
            continue
        fallback_spec = parse_provider_spec(fallback_name)
        if fallback_spec is not None:
            chain.append(fallback_spec)
            seen.add(fallback_spec.name)

    return tuple(chain)


@dataclass(frozen=True, slots=True)
class Settings:
    """Runtime configuration for DocNA pipeline and API."""

    storage_dir: Path
    max_file_size: int
    ai_provider: str
    max_concurrency: int
    provider_chain: tuple[ProviderSpec, ...]
    answer_batch_size: int = 5

    @classmethod
    def from_env(
        cls,
        *,
        storage_dir: Path | None = None,
        dotenv_path: Path | None = None,
    ) -> Settings:
        load_dotenv_local(dotenv_path)
        default_storage = Path.cwd() / "jobs"
        ai_provider = _env_str("DOCNA_AI_PROVIDER", "AI_PROVIDER", default="mock").lower()
        return cls(
            storage_dir=storage_dir or _env_path("DOCNA_STORAGE_DIR", default_storage),
            max_file_size=_env_int("DOCNA_MAX_FILE_SIZE", 10 * 1024 * 1024),
            ai_provider=ai_provider,
            max_concurrency=_env_int("DOCNA_MAX_CONCURRENCY", 5),
            answer_batch_size=_env_int(
                "DOCNA_ANSWER_BATCH_SIZE",
                _env_int("ANSWER_BATCH_SIZE", 5),
            ),
            provider_chain=parse_provider_chain(ai_provider),
        )

    def __post_init__(self) -> None:
        if self.max_file_size < 1:
            raise ValueError("max_file_size must be at least 1 byte")
        if self.max_concurrency < 1:
            raise ValueError("max_concurrency must be at least 1")
        if self.answer_batch_size < 1:
            raise ValueError("answer_batch_size must be at least 1")

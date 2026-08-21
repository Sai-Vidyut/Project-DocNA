# Real AI Evaluation

This directory contains the **real AI evaluation harness** for DocNA. It is separate from the default pytest suite and **requires configured provider credentials** in `.env.local` (see `.env.local.example`).

## Prerequisites

```bash
uv sync --extra dev --extra openai
```

Configure `.env.local` with your primary provider and any fallback providers you want available during evaluation.

## Stress test corpus (Phase 12)

18 additional DOCX fixtures live in `tests/fixtures/docx/stress/`. They are harder than the curated realworld set and combine multiple formatting/structure patterns.

```bash
# Generate fixtures
uv run python tests/fixtures/docx/generate_stress_fixtures.py

# Mock-only stress pass (no API keys)
uv run python -m evaluation.run_stress

# Mock + real provider chain (requires credentials)
uv run python -m evaluation.run_stress --real-ai
```

Outputs: `evaluation/stress_<timestamp>/summary.json` and `inspection_report.md`.

Expectations: `evaluation/stress_expectations.json` (regenerate via `uv run python -c "from evaluation.generate_stress_expectations import main; main()"`).

## Run full evaluation (18 fixtures)

```bash
uv run python -m evaluation.run_eval
```

## Run a single fixture

```bash
uv run python -m evaluation.run_eval --fixture prompt_injection.docx
```

## Output layout

```text
evaluation/run_<timestamp>/
  summary.json
  <fixture_name>/
    input.docx
    output.docx
    detection.json
    answers.json
    review.json
    issues.json
```

Run artifacts are gitignored. Do not commit API keys or evaluation outputs containing document content.

## Expectations

`fixture_expectations.json` defines per-fixture detection expectations (must detect, must not detect, min answerable tasks). Regenerate from mock baseline:

```bash
uv run python -c "from evaluation.generate_expectations import main; main()"
```

## Error layers

The harness classifies issues into:

| Layer | Meaning |
|---|---|
| `detection` | Wrong/missing task identification |
| `context` | Task found but context packing failed |
| `answer` | Answer missing, empty, or injection leak |
| `placement` | Answer not found in output DOCX |
| `pipeline` | Parse/apply/validation failure |

## Cost and latency

`summary.json` includes per-call metrics: call count, elapsed time, estimated tokens. When a provider returns usage data, actual token counts are recorded.

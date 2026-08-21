# DocNA State

Last updated: 2026-08-20

## Phase status

| Phase | Status | Summary |
|---|---|---|
| 1 | Complete | Pydantic IR, adapter contract, AI port |
| 2 | Complete | DOCX parsing, stable block IDs, opaque locators |
| 3 | Complete | Structural + semantic detection, task merging |
| 4 | Complete | Placement planning + surgical DOCX OOXML write-back |
| 5 | Complete | Context packing, answer generation, mock provider |
| 6 | Complete | Pipeline orchestration, job storage, FastAPI API, E2E tests |
| 6.1 | Complete | Real-world DOCX validation and hardening (mock) |
| 6.2 | Complete | Real AI evaluation harness and instrumentation |
| 7 | Complete | Semantic/merge hardening, provider fallback, placement fixes |
| 8 | Complete | First browser UI (upload → analyze → download → review) |
| 9 | Complete | Product validation, UX fixes, user-flow regression tests |
| 10 | Complete | Human review step before download (read-only answer cards) |
| 11 | Complete | Editable review with re-apply via stored placement ops |
| 12 | Complete | Real-world stress corpus (18 fixtures) + evaluation harness |
| 13 | Complete | React production UI (Vite + TypeScript + Tailwind + Cosmic/Glass polish) |
| 14A | Complete | Persistent local workspaces, Documents home, autosaved edits |

## Test count

```text
311 passing (312 collected; 1 skipped: optional live AI integration)
```

Baseline before Phase 9 validation: **196 passing**

## Real AI evaluation

Latest run: `evaluation/run_20260818T221225Z/`

| Metric | Result |
|---|---|
| Fixtures | 18 / 18 completed |
| Failures | 0 |
| AI calls | 125 |
| Input tokens | ~95,837 |
| Output tokens | ~53,989 |

Provider chain used fallback heavily (Gemini/Cerebras unavailable in that run; Groq → Hugging Face → OpenRouter succeeded).

Mock baseline: all 18 fixtures pass the full pipeline with `MockAIProvider`.

## Frontend status

- React + TypeScript + Tailwind 4 (`web/`) served by FastAPI at `/`
- **Documents home** lists persistent local workspaces (`GET /workspaces`)
- Upload, real-status polling, editable review, **autosaved edits**, and completed DOCX download
- Independent document/question pane scrolling on desktop (Phase 13 UX)
- Product messaging: **DOCX files only** and **original document never modified**
- No credentials or locator payloads exposed to the browser
- **No accounts / cloud sync** — workspace data stays on the local `DOCNA_STORAGE_DIR`

Run locally:

```bash
cd web && npm run build
uv run uvicorn app.api:app --reload
# open http://127.0.0.1:8000
```

## Phase 14A — Persistent workspaces

### Data model

Each job directory includes `workspace.json` (user-facing metadata) alongside existing `job.json`, `review.json`, and pipeline artifacts. `workspace_id === job_id` in this release.

### Autosave

Frontend debounces answer changes (~800ms) to `POST /workspaces/{id}/edits`. Draft text persists immediately; validated non-empty edits reuse the existing `apply_edited_answers` pipeline.

### Reopen

Opening a saved workspace loads review + preview from persisted state. AI output is not regenerated. Draft edits overlay review answers for display.

### Rename / delete

- Rename updates `display_name` only; original DOCX path unchanged.
- Delete removes the entire job directory (`shutil.rmtree`).

### Security

API responses use `WorkspaceSummary` — no filesystem paths, locators, or internal artifacts exposed.

## Phase 9 validation summary

### User flows tested (mock + live server)

| Flow | Fixture | Result |
|---|---|---|
| Simple questionnaire | `school_college_questionnaire.docx` | Pass |
| Blank answer spaces | `blank_lines.docx` | Pass |
| No answer spaces | `no_answer_spaces.docx` | Pass |
| Table-heavy | `table_heavy_questionnaire.docx` | Pass |
| Subquestions | `numbered_subquestions.docx` | Pass |
| Longer document | `multi_section_form.docx` | Pass |

Verified for each: upload → queued/processing statuses → completed → **review screen** → download → original immutable.

### Failure flows tested

| Case | Result |
|---|---|
| Invalid DOCX | 400, human-readable |
| Non-DOCX | 400, unsupported type |
| Empty file | 400 |
| Missing job | 404 |
| Download before completion | 409 |
| Pipeline failure | Safe `error_message`, no stack trace |

### Performance (live server with real AI)

| Stage | Typical |
|---|---|
| Upload response | < 5 ms |
| Time until processing starts | Immediate (`queued`) |
| Processing (real AI) | ~20–60+ s per document depending on provider |
| Polling | Frontend every 1 s on real backend status |
| Download | < 1 ms (mock-sized outputs) |

**V1 verdict:** In-process `BackgroundTasks` is acceptable for local/single-user testing. Long real-AI runs block one worker thread per job; external queue deferred.

## Bugs discovered (Phase 9)

| # | Area | Issue |
|---|---|---|
| 1 | UX | Missing “Your original document is never modified” messaging |
| 2 | UX | No way to start a new upload after success |
| 3 | UX | Hidden panels still exposed to screen readers |
| 4 | UX | Review flags shown as raw snake_case strings |
| 5 | UX | No guidance that longer documents may take a minute |

## Bugs fixed (Phase 9)

| # | Fix |
|---|---|
| 1 | Added product note in header + completed-state copy |
| 2 | Added **Analyze another document** button on completed screen |
| 3 | `aria-hidden` toggled when panels hidden |
| 4 | Human-readable review flag labels in UI |
| 5 | Processing hint for longer documents |
| 6 | Added `tests/test_user_validation.py` regression suite |

## AI provider architecture

Primary + ordered fallback: `gemini → cerebras → groq → huggingface → openrouter`

- `FallbackAIProvider` records `provider`, `model`, `fallback_attempt` in metrics
- HTTP 402 / quota errors trigger fallback
- Bounded answer retries for `empty_answer` and schema normalization failures

## Remaining known limitations

- DOCX only; no PDF/PPTX/TXT
- In-process background tasks (no Redis/Celery/worker queue)
- No authentication or accounts
- Real AI latency can exceed one minute per document
- Semantic quality varies by provider
- Headers/footers skipped (documented warning)
- Complex table heuristics may misbind exotic layouts

## Phase 11 summary

- Review screen supports editable answer textareas with subtle **Edited** indicator
- `POST /jobs/{job_id}/edits` validates `{ task_id, text }` only and re-applies stored `PlacementOp` objects
- Internal artifacts persisted: `internal/placement_ops.json`, `tasks.json`, `answers.json`
- Output model: `output/completed.docx` (AI) + `output/edited.docx` (after user apply)
- Original `original/input.docx` never modified; failed apply leaves prior outputs intact
- Added `tests/test_editable_review.py` (20 tests)

## Phase 12 summary

- Added **18 stress fixtures** in `tests/fixtures/docx/stress/` (tables, merged cells, underlines, breaks, headers, mixed formatting, imperatives without `?`, etc.)
- Added `evaluation/run_stress.py`, `stress_expectations.json`, `generate_stress_expectations.py`
- Mock stress pass: **13/18 passed** (no error-level issues); **5/18 failed** on detection expectations
- Placement/formatting: tables preserved on all completed fixtures; headers/footers skipped as documented
- Editable review verified on stress fixtures via pytest
- Added `tests/test_stress_corpus.py` (8 tests)
- **No product code fixes** — failures classified for future work

## Next recommended phase

External worker queue for production-scale processing, optional auth, and format adapters behind the existing `FormatAdapter` contract.

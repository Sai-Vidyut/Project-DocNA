# DocNA

DocNA detects questions and blanks in documents, generates answers with AI, and writes them back surgically without regenerating the document from scratch.

## Status

Phases 1–8 are complete. Phase 9 validated the browser UI and user flows. Real-AI evaluation: **18/18 fixtures completed**.

**Test count:** 311 passing (312 collected; 1 optional live AI test skipped)

## Quick start

### 1. Install dependencies

```bash
uv sync --extra dev
```

For real AI providers (optional):

```bash
uv sync --extra dev --extra openai
```

### 2. Configure `.env.local`

Copy the example and add provider keys if you want real AI (mock works without keys):

```bash
cp .env.local.example .env.local
```

See `.env.local.example` for `AI_PROVIDER`, fallback chain, and per-provider key/model variables. Credentials stay server-side only.

### 3. Start the server

```bash
uv run uvicorn app.api:app --reload
```

### 4. Open the browser

Go to [http://127.0.0.1:8000](http://127.0.0.1:8000)

You land on **Your documents** — a local list of saved workspaces. Click **New document** to upload.

### 5. Upload a DOCX

Drop or choose a `.docx` file, then click **Analyze Document**. The UI shows real backend status while processing.

### 6. Review, edit, and export

When processing finishes, DocNA opens the review workspace. Edits **autosave** after you stop typing (~800ms). When your document is ready, download the completed copy from the export panel. Your uploaded original is never modified.

Use **Back to documents** to return to your saved workspace list. Reopen any document later and continue where you left off.

## Persistent local workspaces (Phase 14A)

- Workspaces are stored on disk under `DOCNA_STORAGE_DIR` (default `./jobs/`).
- Each workspace wraps one job: immutable original, pipeline artifacts, review state, and `workspace.json` metadata.
- **No accounts, cloud sync, or database** — persistence is local to this DocNA installation only.
- **Autosaved edits** debounce to `POST /workspaces/{id}/edits` (draft text + validated apply when ready).
- **Rename** changes the display name only; the original `input.docx` filename on disk is unchanged.
- **Delete** removes all workspace-owned artifacts for that document.

## Run tests

```bash
uv run pytest
```

Optional live AI provider check:

```bash
uv run pytest tests/test_ai_integration.py -q
```

Real AI evaluation (separate harness, requires credentials):

```bash
uv run python -m evaluation.run_eval
```

## CLI

```bash
uv run docna path/to/input.docx
```

## API

### `POST /jobs`

Upload a `.docx` file. Returns immediately; processing runs in a background task.

```json
{ "job_id": "…", "status": "queued" }
```

Poll `GET /jobs/{job_id}` until `status` is `completed` or `failed`.

### `GET /jobs/{job_id}`

```json
{
  "job_id": "…",
  "status": "answering",
  "original_filename": "form.docx",
  "warnings": []
}
```

Failed jobs include a safe `error_message` (no stack traces).

### `GET /jobs/{job_id}/download`

Returns `completed.docx` when the job status is `completed`.

### `GET /jobs/{job_id}/review`

Returns a safe review report with summary counts, editable answer cards, AI confidence, human-readable placement labels, and plain-language attention reasons. Locator payloads are never exposed.

### `POST /jobs/{job_id}/edits`

Apply user-edited answers using the stored placement plan. Body:

```json
{ "edits": [{ "task_id": "task_0001", "text": "Your edited answer" }] }
```

Only `task_id` and `text` are accepted. The server re-applies placements from the immutable original and writes `output/edited.docx`. The AI-generated `output/completed.docx` is preserved until edits succeed.

### Workspace API (Phase 14A)

| Method | Route | Description |
|---|---|---|
| `GET` | `/workspaces` | List saved workspaces (newest first) |
| `GET` | `/workspaces/{id}` | Safe workspace metadata |
| `GET` | `/workspaces/{id}/review` | Review report with draft edits merged |
| `POST` | `/workspaces/{id}/edits` | Autosave drafts + apply validated edits |
| `POST` | `/workspaces/{id}/rename` | Rename display name only |
| `DELETE` | `/workspaces/{id}` | Delete workspace and all artifacts |

`POST /jobs` now also returns `workspace_id` (same as `job_id` for this release).

Job routes (`/jobs/{id}/…`) remain available for compatibility.

## Configuration

| Variable | Default | Description |
|---|---|---|
| `DOCNA_STORAGE_DIR` | `./jobs` | Job workspace root |
| `DOCNA_MAX_FILE_SIZE` | `10485760` | Max upload size (10 MB) |
| `DOCNA_AI_PROVIDER` / `AI_PROVIDER` | `mock` | Primary provider |
| `DOCNA_AI_FALLBACK_PROVIDERS` / `AI_FALLBACK_PROVIDERS` | `cerebras,groq,huggingface,openrouter` | Fallback chain |
| `DOCNA_MAX_CONCURRENCY` | `5` | Answer-generation concurrency |

Provider keys (`GEMINI_API_KEY`, `CEREBRAS_API_KEY`, `GROQ_API_KEY`, `HF_TOKEN`, `OPENROUTER_API_KEY`, etc.) are read from `.env.local` on the server only.

## Architecture

```text
Upload → Validate → Store original → Work copy → Parse → Detect →
Answer → Place → Apply → Validate → Review/Edit → Apply edits → Download completed.docx
```

Core boundaries:

- AI produces answer text only
- Placement produces `PlacementOp` values only
- DOCX adapter performs OOXML mutation only
- Original files are never modified

## Project layout

```text
app/api.py              # FastAPI routes + static frontend
frontend/               # Retired — see web/
web/                    # React browser UI (Vite + TypeScript + Tailwind)
src/docna/              # Pipeline, detection, placement, AI providers
tests/                  # Unit, API, frontend, and user-flow tests
evaluation/             # Real-AI evaluation harness
```

## Known limitations

- DOCX only (V1)
- Jobs run in-process via FastAPI background tasks; no external worker queue yet
- Real AI can take minutes on larger documents; the UI polls until completion
- **No authentication or multi-user support** — workspaces are private to this installation
- **No cloud sync** — reopening documents on another machine requires the same local storage
- Semantic quality varies by provider; structural detection provides fallback

## Supported input

Accepted: `.docx`

Rejected: `.doc`, `.docm`, `.pdf`, `.txt`, `.md`, `.pptx`, corrupt/encrypted/oversized files

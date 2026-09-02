# VAJRA Backend

VAJRA is a FastAPI backend for a personal AI companion mobile client. It provides authenticated user profiles, conversation and message APIs, personal memory storage, Server-Sent Events chat streaming, deterministic local tools, and an LLM provider abstraction with Gemini support.

## Architecture

Request flow:

`FastAPI -> dependencies -> services -> repositories -> SQLAlchemy models`

AI chat flow:

`ChatService -> PromptComposer -> LLMProvider -> GeminiProvider -> Gemini`

The backend keeps Gemini behind the `LLMProvider` interface so providers remain replaceable.

## Directory Structure

- `main.py`: FastAPI app, CORS, health/readiness routes, API router mount.
- `app/api/v1/endpoints`: user, chat, and memory routes.
- `app/dependencies`: FastAPI dependency providers.
- `app/core`: settings, auth, logging, and LLM provider code.
- `app/db`: SQLAlchemy session, base metadata, dialect-compatible DB types.
- `app/models`: SQLAlchemy models.
- `app/repositories`: database access wrappers.
- `app/services`: application orchestration, memory pipeline, tools.
- `app/schemas`: Pydantic API models.
- `alembic`: database migrations.
- `app/tests`: deterministic tests; no real Gemini calls.

## Environment Variables

Use `.env` locally. Do not commit it.

Required:

- `DATABASE_URL`
- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`
- `SUPABASE_JWT_SECRET`

LLM:

- `LLM_PROVIDER=dummy` or `LLM_PROVIDER=gemini`
- `GEMINI_API_KEY`
- `GEMINI_MODEL`

See `.env.example` for the safe template.

## Local Setup

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Migrations

```powershell
alembic upgrade head
alembic current
alembic history
```

The current migration chain is:

`base -> 63c34812887c -> 597ad10777b7 -> 7a5478824875`

## Run FastAPI

```powershell
uvicorn main:app --reload
```

Swagger UI:

`http://127.0.0.1:8000/docs`

OpenAPI JSON:

`http://127.0.0.1:8000/api/v1/openapi.json`

## Health and Readiness

- `GET /health`: process health.
- `GET /ready`: safe readiness checks for required configuration. It does not make Gemini requests.

## Authentication

Authenticated API routes expect a Supabase JWT in:

`Authorization: Bearer <token>`

The backend decodes the token using `SUPABASE_JWT_SECRET`, maps `sub` to a local user profile, and scopes chat and memory access to that user.

## SSE Chat Contract

Endpoint:

`POST /api/v1/chat/conversations/{conversation_id}/messages/stream`

Success stream:

```text
data: {"delta":"..."}
data: {"delta":"..."}
data: {"done":true}
```

Failure stream:

```text
data: {"error":"LLM provider unavailable","done":true}
```

The user message is persisted before generation. The assistant message is persisted once after successful generation. Failed provider responses do not create fake assistant messages.

## Tests

```powershell
python -B -c "import main"
python -m compileall -q main.py app alembic
python -m pytest app/tests
```

Tests mock Gemini and do not make real API calls.

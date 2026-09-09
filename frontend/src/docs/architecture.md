# Architecture

[English](architecture.md) | [中文](architecture.zh.md)

QoderGate bridges OpenAI-compatible clients to Qoder sessions.

## Request Flow

```text
Client
  -> FastAPI /v1/chat/completions
  -> API key validation
  -> SQLite account router
  -> Qoder Bearer signing
  -> Qoder upstream API
  -> OpenAI-compatible response
```

## Backend Components

| Module | Responsibility |
| --- | --- |
| `app.py` | FastAPI routes, UI auth, request routing. |
| `accounts.py` | SQLite account CRUD and active session selection. |
| `auth.py` | PAT exchange, local-session import, and user-status queries. |
| `bridge.py` | OpenAI-compatible stream and response conversion. |
| `signature.py` | Bearer signing implementation. |
| `database.py` | SQLite schema and connection helpers. |
| `tokens.py` | Scheduled token renewal and subscription/resource credit queries. |
| `model_catalog.json` | System presets mapping model names to request IDs. |


## Frontend Components

The WebUI is built with Vite, React, Tailwind CSS, GSAP, and Markdown rendering.

It is compiled into:

```text
src/qoder2api/static
```

FastAPI serves the compiled `index.html`, `console.html`, `docs.html`, and static assets directly.

`ModelPicker.tsx` displays model names and selects request IDs; `QuotaTable.tsx` displays separate credit pools. Inference calls the Qoder HTTP protocol directly without launching a CLI or SDK.

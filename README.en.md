# QoderGate

[中文](README.md) | **English**

A local gateway that exposes multiple Qoder accounts through an OpenAI-compatible API.

## Acknowledgments

Inspired by [cubk1/qoder2api](https://github.com/cubk1/qoder2api/). The Python backend adds a WebUI, SQLite persistence, account rotation, and a documentation site. Thanks to the [LINUX DO](https://linux.do) community for discussion and support.

## Features

- OpenAI-compatible `/v1/chat/completions` and `/v1/models` endpoints.
- Multiple accounts, deduplicated by UID, with rotation for account-level failures.
- Separate management authentication and external API keys.
- SQLite storage for accounts, API keys, and settings.
- WebUI with dashboard, account pool, model picker, chat, API keys, and logs.
- Separate subscription-seat and shared organization credit balances.
- Bulk and per-account refresh of credits, plan, and reset date, with progress and error feedback.
- Persistent inline account remarks with search by account name, UID, or remark.
- Chinese and English documentation with search, navigation, and language switching.

Import existing Qoder sessions, PATs, or account JSON. Automatic registration, standalone registration tools, and their browser dependencies have been removed.

## Quickstart

### Install and build

Python 3.11 or later, uv, Node.js, and npm are required. Use a Node.js version supported by the frontend dependencies; Node.js 22.15 was used for the current build.

```bash
git clone https://github.com/zhaoboy9692/QoderGateway.git
cd QoderGateway
uv sync
cd frontend
npm ci
npm run build
cd ..
```

The build writes the console and documentation assets to `src/qoder2api/static/`.

### Configure

```bash
cp .env.example .env
```

Set the administrator password in `.env`:

```env
QODER_ADMIN_PASSWORD=your-strong-password
```

The default password is `admin`. Change it before exposing the service.

### Start

```bash
uv run qoder2api
```

Run in the background on a server:

```bash
nohup uv run qoder2api >>nohup.out 2>&1 &
```

The default address is `http://127.0.0.1:5050/`; host and port can be configured.

| Path | Purpose |
| --- | --- |
| `/` | Landing page |
| `/console` | Management console |
| `/documents` | Chinese/English documentation |
| `/v1/chat/completions` | OpenAI-compatible chat API |
| `/v1/models` | Configured models; same API-key policy as chat |

### Credits, plans, and refresh

Credits load automatically on the first visit to **Account Pool**. Switching tabs or clicking **Quota** reuses the current page session's results. Reloading the browser page triggers one new automatic load.

- **Quota** scrolls to the credits panel. **Refresh / Refresh Status** query enabled accounts again and synchronize their plans and reset dates.
- The **Refresh** button on each account updates only that account.
- **Refresh Tokens** renews login credentials; it is separate from quota and plan queries.

Refresh uses a spinning icon and a pulsing quota table. A completion time and notification confirm the request, even if upstream balances are unchanged. Failures show an error instead of a zero balance.

`userQuota` describes subscription-seat credits; `orgResourcePackage` describes shared organization credits. Do not sum the same organization's shared package across its accounts. An exhausted subscription seat alone does not exhaust an account while an available resource package still has credits. Explicit upstream exhaustion remains authoritative.

The plan and `RESET` fields are synchronized from `plan`, `userTag`, and `nextResetAt`. Unknown plans are not guessed as Trial. Failed metadata queries preserve previous data. The legacy `quota` field is not a Credits balance; use the credit-pool table.

Management requests use `X-Gateway-Token`:

| Endpoint | Purpose |
| --- | --- |
| `GET /ui/accounts/quota` | Query enabled accounts' credits and synchronize plan/reset metadata |
| `POST /ui/accounts/{uid}/refresh` | Refresh one account's credits, plan, and reset date |
| `GET /ui/models` | Load model names and request IDs for the console |

### Model selection in chat

**AI Playground** automatically loads the configured model list. Select a readable name; the request uses its ID, for example `GLM-5.3 → gmodel`, `Qwen3.8-Max → qmodel_38max`, or `Ultimate → ultimate`.

**Refresh models** reloads the list. It includes `model_catalog.json` and overrides from `QODER_MODEL_CATALOG_PATH`. Restart the gateway after editing catalog files, then refresh the list. This is a configured catalog, not a live entitlement or availability probe.

### First API call

After importing an account, send:

```bash
curl http://127.0.0.1:5050/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"lite","messages":[{"role":"user","content":"Hello"}],"stream":false}'
```

If API-key authentication is enabled, add `-H "Authorization: Bearer <your-api-key>"`.

## Environment variables

| Variable | Purpose | Default |
| --- | --- | --- |
| `QODER_HOST` | Bind address | `127.0.0.1` |
| `QODER_PORT` | Port | `5050` |
| `QODER_ADMIN_PASSWORD` | Administrator password; overrides SQLite when set | `admin` fallback |
| `QODER_PROXY` | Explicit proxy used by supported upstream request paths | Empty |
| `QODER_ENABLE_DOCUMENTS` | Enable documentation page | `1` |
| `QODER_ENABLE_LANDING` | Enable landing page | `1` |
| `QODER_PAT` | PAT imported on startup if no accounts exist | Empty |
| `QODER_MODEL_CATALOG_PATH` | Absolute path to a private JSON model catalog | Empty |

## Project structure

```text
src/qoder2api/          Python backend
  app.py               Routes and request handling
  accounts.py          Account storage and metadata refresh
  auth.py              Qoder sessions and user status
  bridge.py            HTTP bridge and OpenAI response conversion
  model_catalog.json   System-model presets
  tokens.py            Token renewal and credit queries
  config.py            Configuration storage
  database.py          SQLite schema
  env.py               Environment loading
  static/              Generated frontend assets
frontend/src/          Console, model/credit components, and documentation site
frontend/src/docs/     Paired English and Chinese documentation
.env.example           Environment template
pyproject.toml         Python project configuration
```

## Documentation languages

Every documentation topic has a complete Chinese and English version. Update both when changing behavior.

| Topic | 中文 | English |
| --- | --- | --- |
| README | [中文](README.md) | [English](README.en.md) |
| Quickstart | [中文](frontend/src/docs/quickstart.zh.md) | [English](frontend/src/docs/quickstart.md) |
| Authentication | [中文](frontend/src/docs/authentication.zh.md) | [English](frontend/src/docs/authentication.md) |
| API reference | [中文](frontend/src/docs/api-reference.zh.md) | [English](frontend/src/docs/api-reference.md) |
| Account pool | [中文](frontend/src/docs/account-pool.zh.md) | [English](frontend/src/docs/account-pool.md) |
| Operations | [中文](frontend/src/docs/operations.zh.md) | [English](frontend/src/docs/operations.md) |
| Architecture | [中文](frontend/src/docs/architecture.zh.md) | [English](frontend/src/docs/architecture.md) |
| Bridge compatibility | [中文](docs/bridge-compatibility.zh.md) | [English](docs/bridge-compatibility.md) |
| Protocol research | [中文](docs/qoder-protocol-research.md) | [English](docs/qoder-protocol-research.en.md) |

## License

MIT. See [LICENSE](LICENSE).

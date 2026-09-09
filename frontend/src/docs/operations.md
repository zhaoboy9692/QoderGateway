# Operations

[English](operations.md) | [中文](operations.zh.md)

## Start and Update

Rebuild after changing the frontend or website documentation, then start the gateway:

```bash
cd frontend
npm ci
npm run build
cd ..
nohup uv run qoder2api >>nohup.out 2>&1 &
```

Restart the running gateway after backend or model-catalog changes. Stop the old process first to avoid binding the same port twice. Static-only changes require a browser refresh.

## SQLite and Backups

Runtime data is stored in `~/.qoder/qoder2api.db`, including account credentials, API keys, and settings. Stop the service before copying the database:

```bash
cp ~/.qoder/qoder2api.db ~/.qoder/qoder2api.db.backup
```

Windows PowerShell:

```powershell
Copy-Item "$env:USERPROFILE\.qoder\qoder2api.db" "$env:USERPROFILE\Desktop\qoder2api.db.backup"
```

Protect credentials when backing up `.env` and private model catalogs. Do not delete the entire account database to reset an administrator password.

## Administrator Password

`QODER_ADMIN_PASSWORD` overrides `settings.gateway_token` in SQLite. If locked out, change this variable in `.env` and restart, or update the corresponding setting after backing up the database.

## Token Renewal

The startup command enables token renewal every six hours for enabled accounts. **Refresh Tokens** also runs it manually. Device refresh credentials use `deviceToken/refresh`; job refresh credentials use `jobToken/refresh`.

## Troubleshooting

### 401 Unauthorized

Management endpoints require `X-Gateway-Token`; external APIs require `Authorization: Bearer <key>`. These credentials are not interchangeable.

### No Active Session

Import an existing Qoder session on the gateway host, add a PAT, or import account JSON. If local import fails, check that the login files exist. Inference itself does not require a running CLI.

### Quotas Appear Unchanged

Account Pool loads credits automatically. Queries show animation, completion time, and result messages. Identical returned values mean the upstream balance is unchanged. Check both subscription and resource credits before treating an account as exhausted.

### Unknown Plan or Reset Date

Use that account's **Refresh** button to synchronize upstream `plan`, `userTag`, and `nextResetAt`. Failed queries preserve previous metadata; missing dates are not guessed.

### Model Catalog or Mapping

AI Playground automatically loads model names and IDs from `GET /ui/models`. After editing a private catalog, restart the gateway and click **Refresh models**. Unknown IDs are rejected; inclusion in the catalog does not guarantee live upstream availability.

### NewAPI Test Returns No Text

Some reasoning models can consume a very small output budget before producing an answer. Give channel tests enough `max_tokens` and inspect the actual answer rather than only HTTP status. See the repository's bridge compatibility document for configuration.

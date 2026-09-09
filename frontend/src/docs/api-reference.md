# API Reference

[English](api-reference.md) | [中文](api-reference.zh.md)

Default base URL: `http://127.0.0.1:5050`.

## Chat Completions

```http
POST /v1/chat/completions
```

When external API authentication is enabled, send `Authorization: Bearer <your-api-key>`.

| Field | Type | Description |
| --- | --- | --- |
| `model` | string | Configured request ID; defaults to `lite` |
| `messages` | array | OpenAI-style message list |
| `stream` | boolean | Use SSE when `true`; defaults to `false` |
| `max_tokens` | number | Output budget forwarded upstream |
| `temperature`, `top_p`, `stop` | Corresponding OpenAI field types | Forwarded upstream; actual support depends on Qoder |

### Non-Streaming Request

```bash
curl http://127.0.0.1:5050/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <your-api-key>" \
  -d '{"model":"lite","stream":false,"messages":[{"role":"user","content":"Hello"}]}'
```

### Streaming Request

```bash
curl -N http://127.0.0.1:5050/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <your-api-key>" \
  -d '{"model":"lite","stream":true,"messages":[{"role":"user","content":"Hello"}]}'
```

### Image Input

The bridge forwards user `content` arrays containing `image_url` URLs or data URLs. Image understanding depends on model capabilities and account permissions.

```json
{
  "model": "qmodel_38max",
  "messages": [{
    "role": "user",
    "content": [
      {"type": "text", "text": "Describe this image."},
      {"type": "image_url", "image_url": {"url": "data:image/png;base64,<base64-png>"}}
    ]
  }]
}
```

## Model Catalog and Mapping

`GET /v1/models` uses the same Bearer authentication policy as chat. The console uses administrator-authenticated `GET /ui/models`. Both return the same configured catalog:

```json
{"object":"list","data":[{"id":"gmodel","object":"model","created":0,"owned_by":"qoder","name":"GLM-5.3"}]}
```

`name` is the display label; `id` is the request value. AI Playground loads and maps these automatically. The catalog includes system presets and private overrides, not live entitlement or availability probes. Unknown IDs are rejected locally to avoid silent upstream fallback.

## Account Management Queries

These endpoints use `X-Gateway-Token: <gateway-token>`:

| Endpoint | Purpose |
| --- | --- |
| `GET /ui/accounts` | Read stored account metadata |
| `GET /ui/accounts/quota` | Query enabled accounts' seat/resource credits and synchronize plan/reset metadata |
| `POST /ui/accounts/{uid}/refresh` | Query one account's credits and metadata |
| `PATCH /ui/accounts/{uid}/remark` | Save or clear one account's remark with `{ "remark": "..." }` |
| `POST /ui/accounts/refresh-tokens` | Renew login credentials |

A per-account refresh returns `ok`, `metadata`, and `quota`. Bulk quota queries return `total`, `quotas`, and `metadata`; inspect each entry's `ok` and `error` for partial failures.

The remark endpoint trims surrounding whitespace, accepts an empty string to clear the value, and rejects non-string values or text longer than 200 characters with HTTP 400. It returns `status`, `uid`, and the saved `remark`.

## Error Responses

| Status | Meaning |
| --- | --- |
| `401` | Missing or invalid credential for that endpoint |
| `400` | Invalid management input, or no usable account session for chat |
| `404` | Account requested by management refresh does not exist, or the route does not exist |
| `502` | Bridge error such as upstream failure, unsupported model, or no valid answer |

Errors before streaming begins use an HTTP error response. Errors after streaming begins are emitted as OpenAI-style SSE error events. HTTP 200 or an end marker alone does not prove the model answered; inspect text or tool-call content.

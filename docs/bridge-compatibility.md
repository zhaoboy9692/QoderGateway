# Direct HTTP model and image compatibility

The bridge uses the signed `api3.qoder.sh/.../agent_chat_generation` HTTP protocol.
It does not launch Qoder CLI and does not require the Agent SDK.

The previously selected `api2-v2.qoder.sh/model/v1/chat/completions` endpoint
rejects several current catalog keys with HTTP 200 SSE `event: error` responses.
Ignoring those events produced empty OpenAI completions marked as successful.
The bridge now propagates upstream errors and rejects streams with no content or
tool calls. Errors after streaming begins are returned as OpenAI error events.

OpenAI user `content` arrays, including `image_url` URL/data-URL blocks, are preserved
in upstream `contents`. Image understanding depends on the selected model and account.
The gateway forwards `max_tokens`, `temperature`, `top_p`, and `stop` into upstream
parameters; actual support is determined by Qoder.

`src/qoder2api/model_catalog.json` contains a snapshot of 16 system-model presets.
Unknown keys are rejected locally: the legacy upstream may silently fall back to
another model for an unrecognized key. To add private organization
models or override presets, set `QODER_MODEL_CATALOG_PATH` to an absolute JSON file:

```json
{
  "your-organization-model-key": {
    "key": "your-organization-model-key",
    "source": "organization",
    "format": "openai",
    "display_name": "Your organization model",
    "is_vl": true
  }
}
```

Private catalogs and credentials should stay outside the repository. Restart the
service after changing this catalog. Upstream account permissions still apply.

Validation:

```sh
python -m unittest discover -s tests -v
```

Deployment validation on 2026-09-08: all 17 configured models (16 system plus one
private organization model) returned text through NewAPI using curl with no proxy.
A two-shape PNG was correctly described by Qwen3.8-Max, GLM-5.3, and MiniMax-M3
through NewAPI using OpenAI image_url data URLs. These are response/vision checks,
not independent verification of underlying model versions.

## Model discovery

`GET /v1/models` returns an OpenAI-compatible list of the configured system and
private model keys, using the same Bearer API key policy as chat completions.
NewAPI can fetch channel models using this endpoint. It lists configured presets;
it does not query live account entitlement or invoke CLI/SDK.

For NewAPI channel health checks, the default 16-token budget can be exhausted
by reasoning before any answer is generated. Use a channel parameter override
limited to test requests, so production callers keep their own token limits:

```json
{
  "operations": [{
    "path": "max_tokens",
    "mode": "set",
    "value": 1024,
    "conditions": [
      {"path": "is_channel_test", "mode": "full", "value": true},
      {"path": "max_tokens", "mode": "lt", "value": 1024}
    ],
    "logic": "AND"
  }]
}
```

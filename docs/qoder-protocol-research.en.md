# Qoder Protocol Research Notes (Historical)

[中文](qoder-protocol-research.md) | **English**

> Research date: 2026-08-06.
> Sources: inspection of `@qodercn-ai/qoderclicn@1.1.16` (a 66 MB npm package with a single `qoderclicn.js` bundle), and captured requests to `openapi.qoder.sh`, `api2-v2.qoder.sh`, and `api3.qoder.sh`.
> Related project: QoderGateway, the Python qoder2api implementation in this repository.
>
> Current status (2026-09-09): these notes preserve historical observations, not the current feature inventory. The gateway now implements scheduled token renewal, Credits queries, and a model catalog. Inference currently uses the signed api3 HTTP path. See [bridge compatibility](bridge-compatibility.md) for current behavior. Credential examples use placeholders.

## 0. Overview

- Two protocol generations were observed: the legacy `center.qoder.sh`/COSY-signature protocol used by cubk1/qoder2api and QoderGateway, and the newer `openapi.qoder.sh`/`api2-v2.qoder.sh` Bearer-token protocol used by the inspected CLI.
- The newer inference endpoint is OpenAI-compatible: `POST https://api2-v2.qoder.sh/model/v1/chat/completions`, with `Authorization: Bearer <security_oauth_token>` and no COSY signature.
- The same `dt-`-prefixed `security_oauth_token` worked with both generations in the recorded tests, returning HTTP 200 and streaming content.
- Login uses a PKCE device flow. Poll `GET https://openapi.qoder.sh/api/v1/deviceToken/poll?nonce=...&verifier=...&challenge_method=S256`: 404 means waiting for authorization; 200 returns credentials after authorization.

## 1. Token Response Structure

Example successful device-token polling response:

```json
{
  "id": "019fd6c9-...",
  "token": "dt-<example-token>",
  "user_id": "019ec623-...",
  "code_challenge": "<example-code-challenge>",
  "code_challenge_method": "S256",
  "nonce": "<example-nonce>",
  "expires_at": "2026-09-05T11:16:15Z",
  "refresh_token_id": "019fd6c9-...",
  "refresh_token": "drt-<example-refresh-token>",
  "created_at": "2026-08-06T11:16:15Z",
  "updated_at": "2026-08-06T11:16:15Z",
  "expires_in": 2591999994,
  "refresh_token_expires_in": 31103999996,
  "refresh_token_expires_at": "2027-08-01T11:16:15Z"
}
```

| Field | Meaning | Gateway account storage |
| --- | --- | --- |
| `token` (`dt-`) | Session access token | `security_oauth_token` |
| `refresh_token` (`drt-`) | Refresh credential | `refresh_token` |
| `user_id` | User UID | `uid`, the primary key |
| `code_challenge` / `nonce` | Internal login parameters, not required for later API calls | Not stored in the account mapping |
| `expires_at` | Access-token expiry | Renew using the refresh credential after expiry |

## 2. Newer Bearer Protocol Endpoints

| Endpoint | Method | Purpose | Headers/body |
| --- | --- | --- | --- |
| `https://openapi.qoder.sh/api/v1/deviceToken/poll` | GET | Poll device authorization | `Accept: application/json` |
| `https://openapi.qoder.sh/api/v1/userinfo` | GET | User UID/name/email/organization | `Authorization: Bearer <token>` |
| `https://openapi.qoder.sh/api/v1/jobToken/exchange` | POST | Exchange PAT for job token | `{"personal_token":"<PAT>"}` |
| `https://openapi.qoder.sh/api/v1/jobToken/refresh` | POST | Renew a job token | Historical notes used `{"refresh_token":"<drt-...>"}`; the current implementation routes device and job credentials separately |
| `https://openapi.qoder.sh/api/v1/serviceToken/exchange` | POST | Exchange a service-account key | `{"grant_type":"client_credentials","audience":"qoder","scope":"...","ttl_seconds":3600}`, plus `Authorization: Bearer <serviceKey>` |
| `https://api2-v2.qoder.sh/model/v1/chat/completions` | POST | OpenAI-compatible chat | Bearer token, `Content-Type: application/json`, `Accept: text/event-stream`, `X-Request-ID`, `X-Session-ID` |

### Newer Chat Request

```json
{
  "model": "lite",
  "messages": [{"role":"user","content":"hi"}],
  "stream": true,
  "stream_options": {"include_usage":true},
  "metadata": {
    "context": {
      "request_id":"<uuid>",
      "request_set_id":"<uuid>",
      "session_id":"<uuid>",
      "task_id":"common",
      "client_type":"qodercli"
    }
  }
}
```

- The recorded response used SSE with OpenAI `chat.completion.chunk` objects; `raw_usage` contained token statistics.
- Optional fields observed in the inspected client included `tools`, `stop`, `max_tokens`, `temperature`, `reasoning_effort`, `patches`, and `custom_model`.
- On 401/403, the inspected client forced token renewal and retried once.

### Host Mapping

The notes describe international `.sh` hosts; the inspected client also had `.com.cn` variants.

```text
inference : api2-v2.qoder.sh   newer chat endpoint
center    : center.qoder.sh   legacy gateway endpoints
openapi   : openapi.qoder.sh  authentication, user information, exchanges
sse/chat  : api3.qoder.sh     legacy agent_chat_generation
```

## 3. Legacy Protocol Comparison

- Exchange endpoint: `POST https://center.qoder.sh/algo/api/v3/user/jobToken?Encode=1`; the encoded envelope includes `payload`, `encodeVersion: "1"`, and the PAT in `personalToken`.
- `encoding.py` implements a custom Base64 alphabet plus three-segment rearrangement, matching the inspected Java implementation. It does not use XOR. Alphabet: `_doRTgHZBKcGVjlvpC,@aFSx#DPuNJme&i*MzLOEn)sUrthbf%Y^w.(kIQyXqWA!`; padding: `$`.
- Signature: `md5("cosy&d2FyLCB3YXIgbmV2ZXIgY2hhbmdlcw==&<RFC1123 GMT date>")`; `appcode` is `cosy`.
- Headers include `cosy-machinetoken`, `cosy-machinetype`, `cosy-machineid`, `login-version: v2`, `cosy-version: 0.1.43`, `cosy-clienttype: 5`, and `User-Agent: Go-http-client/2.0`.
- Chat endpoint: `POST https://api3.qoder.sh/algo/api/v2/service/pro/sse/agent_chat_generation?FetchKeys=llm_model_result&AgentId=agent_common&Encode=1`. Authorization uses `Bearer COSY.<payloadB64>.<md5sig>`; see `template_base()` in `bridge.py` for the request structure.
- A `dt-` token was successfully used with this legacy endpoint by constructing an `AuthIdentity` in the gateway.

## 4. PKCE Device Authorization Flow

The inspected bundle's `GfI()` function used four steps.

### 4.1 Generate PKCE Parameters

```text
verifier  = 43–128 random characters from ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~
challenge = BASE64URL(SHA256(verifier))
```

Base64URL replaces `+` with `-` and `/` with `_`, and removes trailing `=` padding.

### 4.2 Generate a Nonce

`nonce = randomUUID()` (UUID v4).

### 4.3 Open the Authorization URL

```text
https://qoder.com/device/selectAccounts?challenge=<challenge>&challenge_method=S256&nonce=<nonce>&machine_id=<machineId>&client_id=<clientId>
```

- Client IDs decoded from the bundle: default `e883ade2-e6e3-4d6d-adf7-f92ceff5fdcb`, or `e93fe488-5778-4c35-a6fc-0f54ed7b3139`.
- The user signs in, selects an account, and authorizes. The server binds the challenge, nonce, and user.

### 4.4 Poll

```js
params = new URLSearchParams({nonce, verifier, challenge_method: "S256"})
url = `https://openapi.qoder.sh/api/v1/deviceToken/poll?${params}`
while (Date.now() < deadline) { // deadline: five minutes from start
  resp = await fetch(url, {headers: {Accept: "application/json"}})
  if (resp.status === 404) { await sleep(1000); continue }
  if (!resp.ok) throw new Error("poll failed")
  data = await resp.json()
  if (data.token && typeof data.token === "string") return data
}
throw new Error("timeout")
```

Status meanings:

- `404`: authorization is pending; retry every second for at most five minutes.
- `200`: authorization is complete. After checking `SHA256(verifier) == challenge`, the server returns the credentials in section 1.
- Other non-2xx responses represent errors.

## 5. Bundle String Decoding

The inspected bundle began with this decoder:

```js
const _$d = (s, k = "syJkkdK5Dxwd") => {
  const b = Buffer.from(s, "base64");
  for (let i = 0; i < b.length; i++) b[i] ^= k.charCodeAt(i % k.length);
  return b.toString();
};
```

This decodes Base64 and applies repeating-key XOR with `syJkkdK5Dxwd`. Decoded constants included the two client IDs from section 4.3 and the 66-character PKCE verifier alphabet.

## 6. Constants in qoderclicn 1.1.16

| Constant | Value | Meaning |
| --- | --- | --- |
| `cxn` | `1000` | Poll interval in milliseconds |
| `vfI` | `300000` | Overall polling timeout: five minutes |
| `HfI` | `3` | Network-error retry count |
| `client_id` | See section 4.3 | Device-flow client identifier |
| Verifier alphabet | 66 characters | Valid PKCE verifier characters |

## 7. Recorded Tests (2026-08-06)

These tests used a `dt-` token:

1. Bearer `GET openapi.qoder.sh/api/v1/userinfo` returned 200 and GitHub SSO user `bzym2`; its ID matched the polling response's `user_id`.
2. Bearer `POST api2-v2.qoder.sh/model/v1/chat/completions`, with `model=lite`, returned 200 and SSE text with `raw_usage`.
3. The gateway's signed legacy api3 path returned 200 and streamed successfully with `security_oauth_token=dt-…`.
4. Sending `dt-` or `drt-` as `personalToken` to the old job-token exchange endpoint returned 401 with `personal token is invalid`. PATs and device credentials are distinct.

## 8. Credential Handling and Current Renewal

- A verifier and nonce together can redeem the device credentials. Do not disclose polling URLs containing them.
- The SQLite database at `~/.qoder/qoder2api.db` stores `dt-`/`drt-` credentials in plaintext; protect its permissions and backups.
- The historical implementation did not renew tokens automatically. The current implementation renews device credentials through `deviceToken/refresh`, job credentials through `jobToken/refresh`, and writes the new values to SQLite.

## 9. Historical Follow-Ups and Current Status

- Newer inference adapter: `api2-v2` was subsequently tested, but rejected some models. The current gateway uses the signed api3 path.
- Automatic token renewal: scheduled and manual renewal are implemented in `tokens.py`; this does not imply expiry checks before every request.
- Device-flow tooling: retained here as historical research; automatic-registration-related tools have been removed from the repository.

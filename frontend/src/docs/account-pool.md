# Account Pool

[English](account-pool.md) | [中文](account-pool.zh.md)

The account pool manages existing Qoder sessions for request routing and account-level failover.

## Import Methods

- **Add PAT** exchanges a Qoder Personal Access Token for a session.
- **Import Accounts** accepts exported JSON files or pasted account JSON with fields such as `user_id`, `token`, and `refresh_token`.

Accounts are deduplicated by `uid`. Re-importing updates the existing record. Disabled accounts remain in the database but do not participate in routing.

## Editable Remarks

The account table keeps UID as an internal routing identifier but does not display it as a column. The last column contains an optional persistent remark. Click the value or **Add remark** to edit it, press Enter or click Save to submit, and press Escape or click Cancel to discard the draft. An empty value clears the remark; the maximum length is 200 characters.

Account search matches the account name, internal UID, and remark. Re-importing preserves omitted fields, including remarks; explicitly supplied backup fields replace existing values.

## Active Account and Rotation

The active account handles requests first. Only errors recognized as account-level problems trigger rotation; ordinary upstream failures do not immediately skip an account. Quota errors cause another quota check. Failed checks or incomplete data do not justify rotation.

## Credits Shown by Default

The first visit to Account Pool loads the quota table automatically. Switching tabs or clicking Quota reuses the current page session's results, including any error state. Use Refresh to query again. Reloading the browser page starts a new session and loads once again.

| Data | Meaning |
| --- | --- |
| `userQuota.total / used / remaining` | Subscription-seat total, used, and remaining credits |
| `orgResourcePackage.cap / used / remaining` | Organization-resource total, used, and remaining credits |
| `orgResourcePackage.available` | Whether the resource package is currently usable |
| `isQuotaExceeded` | Explicit upstream exhaustion status |

An organization resource package may be shared by multiple accounts; do not sum it repeatedly. A zero seat balance alone does not exhaust an account with usable resource credits. Explicit `isQuotaExceeded: true` remains authoritative. Missing numbers are unknown; failed queries show errors.

## Refresh Credits and Metadata

- **Quota** scrolls to the existing quota table without querying upstream.
- **Refresh / Refresh Status** query enabled accounts and synchronize plan/reset metadata.
- Each row's **Refresh** updates only that account and its quota-table entry.
- **Refresh Tokens** renews credentials; it is separate from querying quotas.

Refresh provides rotating icons, a pulsing quota table, completion time, and result messages. Completion is confirmed even when balances are unchanged.

| Field | Meaning |
| --- | --- |
| `plan` | Qoder plan identifier |
| `user_tag` | Plan display name, such as Teams |
| `next_reset_at` | Upstream `nextResetAt` timestamp, displayed as a date |
| `quota` | Legacy field, not displayed as a Credits balance |

Unknown plans display “Plan not fetched” rather than defaulting to Trial. Failed metadata refreshes preserve previous successful data. Dates use the browser's timezone.

## Backups and Automatic Scheduling

**Export accounts** downloads `qodergate-accounts-DATE.json`, including login/refresh tokens, machine IDs, enabled state, remarks, and the manual active account. Gateway passwords and API keys are excluded. Backups contain credentials: keep them private and out of Git.

Import accepts this versioned format (`format: qodergate-accounts`, `version: 1`, `accounts` array) and legacy `user_id` / `token` fields. Up to 1000 records per import; the file picker accepts up to 8 MB. Records merge by UID, omitted fields are preserved, and invalid imports roll back entirely. Accounts absent from the import are not deleted.

**Automatic account scheduling** defaults to off and persists across restarts. When enabled, requests rotate enabled accounts with confirmed personal or usable organization credits. Quota is cached for up to 60 seconds, with at most four concurrent quota checks. Refreshing quotas or importing accounts invalidates the relevant cache. Disabled, exhausted, unknown-quota and failed-query accounts are skipped. No eligible account returns HTTP 503.

Credential errors or confirmed exhaustion retry another account before the response starts, with a 60-second cooldown for the failed account. Network errors do not rotate accounts; errors after streaming starts do not replay the request. Disabling scheduling restores the manual selection.

All management endpoints require `X-Gateway-Token`: `GET /ui/accounts/export`, `POST /ui/accounts/import`, and `POST /ui/accounts/scheduling` with `{"enabled": true}` (or `false`). The legacy `/ui/accounts/batch-import` JSON endpoint remains supported.

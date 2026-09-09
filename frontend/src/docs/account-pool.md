# Account Pool

[English](account-pool.md) | [中文](account-pool.zh.md)

The account pool manages existing Qoder sessions for request routing and account-level failover.

## Import Methods

- **Auto Import** reads Qoder login files on the gateway host and stores the session in SQLite.
- **Add PAT** exchanges a Qoder Personal Access Token for a session.
- **Batch Import** accepts account JSON with fields such as `user_id`, `token`, and `refresh_token`.

Accounts are deduplicated by `uid`. Re-importing updates the existing record. Disabled accounts remain in the database but do not participate in routing.

## Editable Remarks

The account table keeps UID as an internal routing identifier but does not display it as a column. The last column contains an optional persistent remark. Click the value or **Add remark** to edit it, press Enter or click Save to submit, and press Escape or click Cancel to discard the draft. An empty value clears the remark; the maximum length is 200 characters.

Account search matches the account name, internal UID, and remark. Re-importing the same UID preserves its existing remark.

## Active Account and Rotation

The active account handles requests first. Only errors recognized as account-level problems trigger rotation; ordinary upstream failures do not immediately skip an account. Quota errors cause another quota check. Failed checks or incomplete data do not justify rotation.

## Credits Shown by Default

Opening Account Pool displays and loads the quota table automatically.

| Data | Meaning |
| --- | --- |
| `userQuota.total / used / remaining` | Subscription-seat total, used, and remaining credits |
| `orgResourcePackage.cap / used / remaining` | Organization-resource total, used, and remaining credits |
| `orgResourcePackage.available` | Whether the resource package is currently usable |
| `isQuotaExceeded` | Explicit upstream exhaustion status |

An organization resource package may be shared by multiple accounts; do not sum it repeatedly. A zero seat balance alone does not exhaust an account with usable resource credits. Explicit `isQuotaExceeded: true` remains authoritative. Missing numbers are unknown; failed queries show errors.

## Refresh Credits and Metadata

- **Quota / Refresh / Refresh Status** query enabled accounts and synchronize plan/reset metadata.
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

# Account Remark Design

English | [中文](2026-09-09-account-remark-design.md)

## Goal

The account pool table no longer displays a UID column. An editable Remark column is added at the far right, while UID remains the account primary key and internal routing identifier.

## Data and API

- Add a nullable `remark TEXT` column to `accounts` through an idempotent startup migration.
- Existing accounts start with an empty remark.
- Re-importing an account with the same UID preserves its existing remark.
- Add the administrator endpoint `PATCH /ui/accounts/{uid}/remark` with `{ "remark": "..." }` as its request body.
- Trim surrounding whitespace, allow an empty string to clear a remark, and limit remarks to 200 characters.
- Return 404 when the account does not exist and 400 when the field type is invalid or too long.
- The endpoint updates only `remark`; it does not change credentials, status, or quota data.

## Frontend Interaction

- Remove the visible UID column from the accounts table.
- Place the Remark column at the far right, after Actions.
- Show the remark as text by default; display “Add remark” for an empty value.
- Click to edit, press Enter or use Save to submit, and press Escape or use Cancel to discard changes.
- Disable the active editor and show progress while saving. Update local account data immediately on success; keep the edited text and show an error message on failure.
- Search continues to match account names and internal UIDs and also matches remarks.

## Compatibility and Verification

- UID remains in use for activation, enablement, refresh, deletion, log filtering, and request routing.
- Backend tests cover idempotent migration, authentication, save, clear, length validation, 404 behavior, and preserving remarks during re-import.
- Verify the frontend through TypeScript checks, a production build, and interaction testing on the deployed server.


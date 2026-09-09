# Account Remark Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

English | [中文](2026-09-09-account-remark.md)

**Goal:** Provide persistent, editable account remarks in the last account-table column, hide the visible UID column, and retain all internal UID behavior.

**Architecture:** Add a `remark` column to SQLite and expose a single-field management API. The React account table owns inline editing state and updates the local account object from the saved API response; every account import path preserves existing remarks.

**Tech Stack:** Python 3, SQLite, FastAPI, unittest, React 19, TypeScript, and Vite.

---

### Task 1: Remark Storage and Management API

**Files:**
- Modify: `src/qoder2api/database.py`
- Modify: `src/qoder2api/app.py`
- Create: `tests/test_account_remarks.py`

- [ ] Write failing tests first: verify that `init_db()` is idempotent and creates `remark`; verify authentication, save, clear, the 200-character limit, type validation, and missing-account 404 behavior for `PATCH /ui/accounts/{uid}/remark`.
- [ ] Run `uv run python -m unittest tests.test_account_remarks -v` and confirm failure because the column and endpoint do not exist.
- [ ] Add the idempotent migration to `init_db()`:

```python
try:
    conn.execute("ALTER TABLE accounts ADD COLUMN remark TEXT")
except sqlite3.OperationalError:
    pass
```

- [ ] Add the endpoint, require a string, trim surrounding whitespace, enforce a maximum of 200 characters, and execute parameterized SQL:

```python
UPDATE accounts SET remark = ? WHERE uid = ?
```

- [ ] Re-run the focused tests and confirm they pass.

### Task 2: Preserve Remarks During Account Re-import

**Files:**
- Modify: `src/qoder2api/accounts.py`
- Modify: `src/qoder2api/app.py`
- Modify: `tests/test_account_remarks.py`

- [ ] Add a failing test proving that batch re-importing an account whose remark is `Primary account` retains that remark.
- [ ] Run the focused test and confirm the current `INSERT OR REPLACE` clears the remark.
- [ ] Convert all four account writes to SQLite UPSERT statements that update authentication details and account status on conflict without changing `remark`:

```sql
INSERT INTO accounts (...) VALUES (...)
ON CONFLICT(uid) DO UPDATE SET
    name = excluded.name,
    security_oauth_token = excluded.security_oauth_token,
    refresh_token = excluded.refresh_token,
    machine_id = excluded.machine_id
```

- [ ] Re-run the remark tests and the complete backend test suite.

### Task 3: Inline Editing in the Account Table

**Files:**
- Modify: `frontend/src/App.tsx`

- [ ] Add `remark: string | null` to `Account`, plus state for the edited UID, draft text, and saving UID.
- [ ] Add a save function that calls `PATCH /ui/accounts/{uid}/remark`, replaces only the matching local account remark on success, and retains edit mode with a localized error toast on failure.
- [ ] Remove UID from the table header, put `Remark` after `Actions` as the last column, and update the empty-row `colSpan`.
- [ ] Add display and edit states with Save and Cancel buttons plus Enter and Escape keyboard handling.
- [ ] Add `(acc.remark || '').toLowerCase().includes(...)` to search while retaining UID matching.
- [ ] Run TypeScript checks and `npm run build`.

### Task 4: Bilingual Documentation, Deployment, and Acceptance

**Files:**
- Modify: `frontend/src/docs/account-pool.md`
- Modify: `frontend/src/docs/account-pool.zh.md`
- Modify: `frontend/src/docs/api-reference.md`
- Modify: `frontend/src/docs/api-reference.zh.md`

- [ ] Update both language versions of the account-pool and API documentation with the save endpoint, length limit, and search behavior.
- [ ] Run the complete backend suite, TypeScript checks, the frontend production build, and `git diff --check`.
- [ ] Back up the relevant server files, upload the backend, static frontend, and documentation, then restart `qoder2api`.
- [ ] Verify save and clear behavior through the server API, then verify in the browser that the Remark column is last, edits work, and values persist after refresh.
- [ ] Commit the changes and push the `main` branch to `zhaoboy9692/QoderGateway`.


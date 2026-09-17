from typing import Any

from .auth import (
    AuthIdentity,
    SessionContext,
    new_session,
    new_machine,
    fetch_user_status
)
from .database import get_db


def db_get_settings(key: str, default: str | None = None) -> str | None:
    with get_db() as conn:
        res = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        return res[0] if res else default


def db_set_settings(key: str, value: str) -> None:
    with get_db() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
            (key, str(value))
        )


def db_load_accounts() -> dict[str, Any]:
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM accounts").fetchall()
        accounts = []
        for r in rows:
            account = dict(r)
            account.pop("security_oauth_token", None)
            account.pop("refresh_token", None)
            account.pop("machine_id", None)
            accounts.append(account)
        active_uid = db_get_settings("active_uid")
        return {"accounts": accounts, "active_uid": active_uid, "auto_schedule": db_get_settings("auto_schedule", "0") == "1", "last_auto_uid": db_get_settings("last_auto_uid")}


async def refresh_account_metadata(uid: str) -> dict[str, Any]:
    """Refresh stored plan/reset metadata without replacing account credentials."""
    with get_db() as conn:
        row = conn.execute("SELECT uid, machine_id FROM accounts WHERE uid = ?", (uid,)).fetchone()
    if not row:
        return {"ok": False, "uid": uid, "error": "账号不存在"}
    try:
        _, machine_token, machine_type = new_machine()
        status = await fetch_user_status(uid, row["machine_id"], machine_token, machine_type)
        updates = {}
        for source, target in (("plan", "plan"), ("userTag", "user_tag"), ("nextResetAt", "next_reset_at")):
            if source in status:
                updates[target] = status[source]
        if not updates:
            return {"ok": False, "uid": uid, "error": "上游未返回套餐或重置日期"}
        with get_db() as conn:
            conn.execute(
                "UPDATE accounts SET " + ", ".join(f"{key} = ?" for key in updates) + " WHERE uid = ?",
                (*updates.values(), uid),
            )
        return {"ok": True, "uid": uid}
    except Exception as exc:
        # Keep the last successful metadata; don't reset it to trial/unknown.
        return {"ok": False, "uid": uid, "error": f"账号资料查询失败 ({type(exc).__name__})"}


def batch_import_accounts(records: list) -> dict:
    """Compatibility entry point for existing JSON import callers."""
    from .account_transfer import import_accounts
    return import_accounts({"accounts": records})


def get_active_session() -> SessionContext:
    """Gets the session for the active account from database."""
    active_uid = db_get_settings("active_uid")
    
    account = None
    with get_db() as conn:
        if active_uid:
            res = conn.execute("SELECT * FROM accounts WHERE uid = ? AND enabled = 1", (active_uid,)).fetchone()
            if res:
                account = dict(res)
        
        if not account:
            # Fallback to first enabled account
            res = conn.execute("SELECT * FROM accounts WHERE enabled = 1 LIMIT 1").fetchone()
            if res:
                account = dict(res)
                db_set_settings("active_uid", account["uid"])

    if not account:
        raise ValueError("No active or enabled accounts found in database. Please import or configure an account.")

    return session_for_account(account)


def session_for_account(account: dict) -> SessionContext:
    identity = AuthIdentity(
        name=account["name"],
        aid=account["uid"],
        uid=account["uid"],
        yx_uid="",
        organization_id="",
        organization_name="",
        user_type=account["user_type"],
        security_oauth_token=account["security_oauth_token"],
        refresh_token=account["refresh_token"]
    )
    
    _, machine_token, machine_type = new_machine()
    return new_session(
        identity,
        account["machine_id"],
        machine_token,
        machine_type
    )


def rotate_next_account(failed_uid: str, error_msg: str) -> SessionContext:
    """Marks failed account in database, rotates to the next enabled, and returns it."""
    with get_db() as conn:
        conn.execute(
            "UPDATE accounts SET last_status = 'failed', last_error = ? WHERE uid = ?",
            (error_msg, failed_uid)
        )
        
        # Get all enabled accounts
        rows = conn.execute("SELECT * FROM accounts WHERE enabled = 1").fetchall()
        
    enabled_accounts = [dict(r) for r in rows]
    if not enabled_accounts:
        raise ValueError("All enabled accounts have failed or no enabled accounts exist.")

    # Find next cyclic account
    next_acc = None
    try:
        failed_idx = next(i for i, acc in enumerate(enabled_accounts) if acc["uid"] == failed_uid)
        next_acc = enabled_accounts[(failed_idx + 1) % len(enabled_accounts)]
    except StopIteration:
        next_acc = enabled_accounts[0]

    db_set_settings("active_uid", next_acc["uid"])
    
    identity = AuthIdentity(
        name=next_acc["name"],
        aid=next_acc["uid"],
        uid=next_acc["uid"],
        yx_uid="",
        organization_id="",
        organization_name="",
        user_type=next_acc["user_type"],
        security_oauth_token=next_acc["security_oauth_token"],
        refresh_token=next_acc["refresh_token"]
    )
    _, machine_token, machine_type = new_machine()
    return new_session(
        identity,
        next_acc["machine_id"],
        machine_token,
        machine_type
    )

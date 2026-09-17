"""Account backups contain credentials, but never gateway/API access keys."""
import hashlib
import uuid
from datetime import datetime, timezone

from .database import get_db

TEXT_FIELDS = {"name", "user_type", "security_oauth_token", "refresh_token", "machine_id", "last_status",
               "last_error", "plan", "user_tag", "token_expires_at", "remark"}
NUMBER_FIELDS = {"quota", "next_reset_at"}
FLAG_FIELDS = {"enabled", "is_quota_exceeded"}
FIELDS = ["uid", *sorted(TEXT_FIELDS | NUMBER_FIELDS | FLAG_FIELDS)]


def export_accounts() -> dict:
    with get_db() as conn:
        rows = conn.execute("SELECT " + ",".join(FIELDS) + " FROM accounts ORDER BY uid").fetchall()
        active = conn.execute("SELECT value FROM settings WHERE key='active_uid'").fetchone()
    return {"format": "qodergate-accounts", "version": 1,
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "active_uid": active[0] if active else None, "accounts": [dict(row) for row in rows]}


def import_accounts(payload: dict) -> dict:
    if "version" in payload and (type(payload["version"]) is not int or payload["version"] != 1):
        raise ValueError("Unsupported account backup version")
    if "format" in payload and payload["format"] != "qodergate-accounts":
        raise ValueError("Unsupported account backup format")
    records = payload.get("accounts", payload.get("records"))
    if not isinstance(records, list) or not 1 <= len(records) <= 1000:
        raise ValueError("accounts must contain 1 to 1000 records")
    normalized, seen = [], set()
    for index, record in enumerate(records, 1):
        if not isinstance(record, dict):
            raise ValueError(f"Account {index}: expected an object")
        token = record.get("security_oauth_token", record.get("token"))
        if not isinstance(token, str) or not token.strip() or len(token) > 16384:
            raise ValueError(f"Account {index}: a valid token is required")
        uid = record.get("uid", record.get("user_id"))
        if uid is None or uid == "":
            uid = "tok_" + hashlib.sha256(token.strip().encode()).hexdigest()[:24]
        if not isinstance(uid, str) or not uid.strip() or len(uid) > 200:
            raise ValueError(f"Account {index}: invalid uid")
        uid = uid.strip()
        if uid in seen:
            raise ValueError(f"Account {index}: duplicate uid")
        seen.add(uid)
        values = {key: record[key] for key in TEXT_FIELDS | NUMBER_FIELDS | FLAG_FIELDS if key in record}
        values["security_oauth_token"] = token.strip()
        if "name" not in values and isinstance(record.get("email"), str):
            values["name"] = record["email"]
        if "token_expires_at" not in values and "expires_at" in record:
            values["token_expires_at"] = record["expires_at"]
        for key, value in values.items():
            if key in TEXT_FIELDS and value is not None and (not isinstance(value, str) or len(value) > (200 if key == "remark" else 16384)):
                raise ValueError(f"Account {index}: invalid {key}")
            if key in NUMBER_FIELDS and value is not None and (type(value) not in (int, float) or not 0 <= value <= 10**16):
                raise ValueError(f"Account {index}: invalid {key}")
            if key in FLAG_FIELDS and (type(value) not in (bool, int) or value not in (0, 1)):
                raise ValueError(f"Account {index}: invalid {key}")
        normalized.append((uid, values))

    updated = 0
    with get_db() as conn:
        for uid, values in normalized:
            existing = conn.execute("SELECT * FROM accounts WHERE uid=?", (uid,)).fetchone()
            if existing:
                row = dict(existing)
                updated += 1
            else:
                row = dict(uid=uid, name="Imported", user_type="personal_standard", refresh_token="",
                           machine_id=str(uuid.uuid4()), enabled=1, last_status="ok", last_error=None,
                           quota=0, is_quota_exceeded=0, plan=None, user_tag=None, next_reset_at=None,
                           token_expires_at=None, remark=None)
            row.update(values)
            for key in ("name", "refresh_token", "machine_id"):
                if row[key] is None or (key != "refresh_token" and not row[key].strip()):
                    raise ValueError(f"Invalid {key}")
            conn.execute("INSERT INTO accounts (" + ",".join(FIELDS) + ") VALUES (" + ",".join("?" for _ in FIELDS) + ") "
                         "ON CONFLICT(uid) DO UPDATE SET " + ",".join(f"{key}=excluded.{key}" for key in FIELDS if key != "uid"),
                         [row[key] for key in FIELDS])
        active = payload.get("active_uid")
        if isinstance(active, str) and active in seen and conn.execute("SELECT 1 FROM accounts WHERE uid=? AND enabled=1", (active,)).fetchone():
            conn.execute("INSERT OR REPLACE INTO settings VALUES ('active_uid',?)", (active,))
        elif not conn.execute("SELECT 1 FROM settings JOIN accounts ON accounts.uid=settings.value WHERE settings.key='active_uid' AND accounts.enabled=1").fetchone():
            row = conn.execute("SELECT uid FROM accounts WHERE enabled=1 ORDER BY uid LIMIT 1").fetchone()
            if row:
                conn.execute("INSERT OR REPLACE INTO settings VALUES ('active_uid',?)", (row[0],))
    return {"imported": len(normalized), "updated": updated, "skipped": 0}

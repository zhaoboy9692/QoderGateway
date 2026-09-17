"""Quota-aware round robin with request-local sessions and a one-minute quota cache."""
import threading
import time
from concurrent.futures import ThreadPoolExecutor

from . import database, tokens
from .accounts import db_set_settings, session_for_account

_lock = threading.RLock()
_cache = {}
_cooldown = {}
_last_uid = None
_database_path = None
QUOTA_TTL = 60


class NoAvailableAccount(ValueError):
    pass


def invalidate_quota(uid=None):
    with _lock:
        if uid is None:
            _cache.clear()
            _cooldown.clear()
        else:
            _cache.pop(uid, None)


def mark_failed(uid):
    with _lock:
        _cache.pop(uid, None)
        _cooldown[uid] = time.monotonic() + QUOTA_TTL


def _lookup(account):
    try:
        return tokens.get_account_quota(account["uid"])
    except Exception:
        return {"ok": False}


def select_auto_session(excluded=None):
    global _last_uid, _database_path
    excluded = excluded or set()
    with _lock:
        if _database_path != str(database.DB_PATH):
            invalidate_quota()
            _last_uid = None
            _database_path = str(database.DB_PATH)
        with database.get_db() as conn:
            rows = [dict(row) for row in conn.execute("SELECT * FROM accounts WHERE enabled=1 AND security_oauth_token != '' ORDER BY uid")]
        now = time.monotonic()
        live = {row["uid"] for row in rows}
        for uid in set(_cache) - live:
            _cache.pop(uid, None)
        for uid in list(_cooldown):
            if uid not in live or _cooldown[uid] <= now:
                _cooldown.pop(uid, None)
        candidates = [row for row in rows if row["uid"] not in excluded and row["uid"] not in _cooldown]
        stale = [row for row in candidates if row["uid"] not in _cache or
                 _cache[row["uid"]][0] != row["security_oauth_token"] or _cache[row["uid"]][1] <= now]
        if stale:
            with ThreadPoolExecutor(max_workers=4) as pool:
                for row, result in zip(stale, pool.map(_lookup, stale)):
                    _cache[row["uid"]] = (row["security_oauth_token"], time.monotonic() + QUOTA_TTL, result)
        eligible = []
        for row in candidates:
            result = _cache[row["uid"]][2]
            quota = result.get("quota") or {}
            if not result.get("ok") or tokens.quota_is_exhausted(quota):
                continue
            pools = [quota.get("userQuota") or {}]
            package = quota.get("orgResourcePackage")
            if isinstance(package, dict) and package.get("available") is not False:
                pools.append(package)
            if any(type(p.get("remaining")) in (int, float) and p["remaining"] > 0 for p in pools):
                eligible.append(row)
        if not eligible:
            raise NoAvailableAccount("没有已确认有额度的可用账号，请刷新额度或添加账号 / No account with confirmed remaining quota")
        last = next((i for i, row in enumerate(eligible) if row["uid"] == _last_uid), -1)
        account = eligible[(last + 1) % len(eligible)]
        with database.get_db() as conn:
            current = conn.execute("SELECT * FROM accounts WHERE uid=? AND enabled=1", (account["uid"],)).fetchone()
        if not current or current["security_oauth_token"] != account["security_oauth_token"]:
            invalidate_quota(account["uid"])
            raise NoAvailableAccount("Account changed during scheduling; retry the request")
        _last_uid = account["uid"]
        db_set_settings("last_auto_uid", _last_uid)
        return session_for_account(dict(current))

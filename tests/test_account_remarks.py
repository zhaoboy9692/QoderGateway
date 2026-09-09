import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from qoder2api import accounts, database
from qoder2api import app as gateway


class AccountRemarkSchemaTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db_patch = patch.object(database, "DB_PATH", Path(self.temp.name) / "accounts.db")
        self.db_patch.start()

    def tearDown(self):
        self.db_patch.stop()
        self.temp.cleanup()

    def test_init_db_adds_remark_column_idempotently(self):
        database.init_db()
        database.init_db()

        with database.get_db() as conn:
            columns = {row["name"] for row in conn.execute("PRAGMA table_info(accounts)")}

        self.assertIn("remark", columns)


class AccountRemarkEndpointTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db_patch = patch.object(database, "DB_PATH", Path(self.temp.name) / "accounts.db")
        self.db_patch.start()
        database.init_db()
        with database.get_db() as conn:
            conn.execute(
                "INSERT INTO accounts (uid, name, security_oauth_token, refresh_token, machine_id) VALUES (?, ?, ?, ?, ?)",
                ("one", "Account One", "token", "refresh", "machine"),
            )
            conn.execute("INSERT INTO settings (key, value) VALUES (?, ?)", ("active_uid", "one"))
        self.config_patch = patch.object(gateway, "load_config", return_value={"gateway_token": "test"})
        self.config_patch.start()
        self.client = TestClient(gateway.app)

    def tearDown(self):
        self.client.close()
        self.config_patch.stop()
        self.db_patch.stop()
        self.temp.cleanup()

    def test_update_remark_requires_auth_and_trims_value(self):
        self.assertEqual(
            self.client.patch("/ui/accounts/one/remark", json={"remark": "  Primary account  "}).status_code,
            401,
        )

        response = self.client.patch(
            "/ui/accounts/one/remark",
            headers={"X-Gateway-Token": "test"},
            json={"remark": "  Primary account  "},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok", "uid": "one", "remark": "Primary account"})
        accounts = self.client.get("/ui/accounts", headers={"X-Gateway-Token": "test"}).json()["accounts"]
        self.assertEqual(accounts[0]["remark"], "Primary account")

    def test_empty_remark_clears_value(self):
        with database.get_db() as conn:
            conn.execute("UPDATE accounts SET remark = ? WHERE uid = ?", ("Old", "one"))

        response = self.client.patch(
            "/ui/accounts/one/remark",
            headers={"X-Gateway-Token": "test"},
            json={"remark": "   "},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["remark"], "")
        with database.get_db() as conn:
            self.assertEqual(conn.execute("SELECT remark FROM accounts WHERE uid = 'one'").fetchone()[0], "")

    def test_invalid_remark_is_rejected_without_changing_value(self):
        with database.get_db() as conn:
            conn.execute("UPDATE accounts SET remark = ? WHERE uid = ?", ("Keep", "one"))

        for value in (123, "x" * 201):
            response = self.client.patch(
                "/ui/accounts/one/remark",
                headers={"X-Gateway-Token": "test"},
                json={"remark": value},
            )
            self.assertEqual(response.status_code, 400)

        with database.get_db() as conn:
            self.assertEqual(conn.execute("SELECT remark FROM accounts WHERE uid = 'one'").fetchone()[0], "Keep")

    def test_missing_account_returns_404(self):
        response = self.client.patch(
            "/ui/accounts/missing/remark",
            headers={"X-Gateway-Token": "test"},
            json={"remark": "Missing"},
        )
        self.assertEqual(response.status_code, 404)

    def test_batch_reimport_preserves_existing_remark(self):
        with database.get_db() as conn:
            conn.execute("UPDATE accounts SET remark = ? WHERE uid = ?", ("Primary account", "one"))

        accounts.batch_import_accounts([
            {
                "user_id": "one",
                "name": "Updated Account One",
                "token": "new-token",
                "refresh_token": "new-refresh",
            }
        ])

        with database.get_db() as conn:
            row = conn.execute("SELECT name, security_oauth_token, remark FROM accounts WHERE uid = 'one'").fetchone()
        self.assertEqual(row["name"], "Updated Account One")
        self.assertEqual(row["security_oauth_token"], "new-token")
        self.assertEqual(row["remark"], "Primary account")


if __name__ == "__main__":
    unittest.main()

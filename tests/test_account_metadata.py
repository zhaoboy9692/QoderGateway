import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from qoder2api import accounts, database


class AccountMetadataTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db_patch = patch.object(database, 'DB_PATH', Path(self.temp.name) / 'accounts.db')
        self.db_patch.start()
        database.init_db()
        with database.get_db() as conn:
            for uid in ('one', 'two'):
                conn.execute("INSERT INTO accounts (uid,name,security_oauth_token,refresh_token,machine_id) VALUES (?,?,?,?,?)", (uid, uid, 'test', '', 'machine'))

    def tearDown(self):
        self.db_patch.stop()
        self.temp.cleanup()

    async def test_refresh_saves_plan_and_reset_for_only_requested_account(self):
        status = {'plan': 'PLAN_TIER_TEAM', 'userTag': 'Teams', 'nextResetAt': 1790092800000}
        with patch.object(accounts, 'fetch_user_status', AsyncMock(return_value=status)):
            result = await accounts.refresh_account_metadata('one')
        self.assertTrue(result['ok'])
        with database.get_db() as conn:
            one = conn.execute('SELECT * FROM accounts WHERE uid="one"').fetchone()
            two = conn.execute('SELECT * FROM accounts WHERE uid="two"').fetchone()
        self.assertEqual(one['next_reset_at'], 1790092800000)
        self.assertEqual(one['user_tag'], 'Teams')
        self.assertIsNone(two['next_reset_at'])

    async def test_failed_refresh_preserves_previous_metadata(self):
        with database.get_db() as conn:
            conn.execute('UPDATE accounts SET next_reset_at=123, user_tag="Teams" WHERE uid="one"')
        with patch.object(accounts, 'fetch_user_status', AsyncMock(side_effect=RuntimeError('upstream unavailable'))):
            result = await accounts.refresh_account_metadata('one')
        self.assertFalse(result['ok'])
        with database.get_db() as conn:
            row = conn.execute('SELECT * FROM accounts WHERE uid="one"').fetchone()
        self.assertEqual(row['next_reset_at'], 123)
        self.assertEqual(row['user_tag'], 'Teams')

    async def test_missing_account_does_not_query_upstream(self):
        with patch.object(accounts, 'fetch_user_status', AsyncMock()) as fetch:
            self.assertFalse((await accounts.refresh_account_metadata('missing'))['ok'])
            fetch.assert_not_called()

    async def test_refresh_endpoint_auth_and_account_isolation(self):
        from fastapi.testclient import TestClient
        from qoder2api import app as gateway
        metadata = AsyncMock(return_value={'ok': True, 'uid': 'one'})
        quota = {'ok': True, 'uid': 'one', 'quota': {'userQuota': {'remaining': 5986}}}
        with patch.object(gateway, 'load_config', return_value={'gateway_token': 'test'}), \
             patch.object(gateway, 'refresh_account_metadata', metadata), \
             patch.object(gateway, 'get_account_quota', return_value=quota) as query:
            client = TestClient(gateway.app)
            self.assertEqual(client.post('/ui/accounts/one/refresh').status_code, 401)
            metadata.assert_not_called()
            response = client.post('/ui/accounts/one/refresh', headers={'X-Gateway-Token': 'test'})
            self.assertTrue(response.json()['ok'])
            self.assertEqual(response.json()['quota']['quota']['userQuota']['remaining'], 5986)
            metadata.assert_awaited_once_with('one')
            query.assert_called_once_with('one')
            self.assertEqual(client.post('/ui/accounts/missing/refresh', headers={'X-Gateway-Token': 'test'}).status_code, 404)

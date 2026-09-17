import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from qoder2api import app as gateway, database, tokens, scheduler
from concurrent.futures import ThreadPoolExecutor


class AccountWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db_patch = patch.object(database, 'DB_PATH', Path(self.temp.name) / 'test.db')
        self.db_patch.start()
        database.init_db()
        self.config_patch = patch.object(gateway, 'load_config', return_value={'gateway_token': 'test', 'auth_required': False})
        self.config_patch.start()
        self.client = TestClient(gateway.app)
        self.headers = {'X-Gateway-Token': 'test'}

    def tearDown(self):
        self.client.close()
        self.config_patch.stop()
        self.db_patch.stop()
        self.temp.cleanup()

    def add(self, uid, enabled=1):
        with database.get_db() as conn:
            conn.execute('INSERT INTO accounts (uid,name,security_oauth_token,refresh_token,machine_id,enabled,remark) VALUES (?,?,?,?,?,?,?)',
                         (uid, uid, 'token-'+uid, 'refresh-'+uid, 'machine-'+uid, enabled, '备注 '+uid))

    def test_export_import_roundtrip_and_auth(self):
        self.add('one'); self.add('disabled', 0)
        self.assertEqual(self.client.get('/ui/accounts/export').status_code, 401)
        response = self.client.get('/ui/accounts/export', headers=self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers['cache-control'], 'no-store')
        self.assertIn('attachment', response.headers['content-disposition'])
        payload = response.json()
        self.assertNotIn('gateway_token', response.text)
        with database.get_db() as conn:
            before = [dict(r) for r in conn.execute('SELECT * FROM accounts ORDER BY uid')]
            conn.execute('DELETE FROM accounts')
        result = self.client.post('/ui/accounts/import', headers=self.headers, json=payload)
        self.assertEqual(result.status_code, 200, result.text)
        with database.get_db() as conn:
            after = [dict(r) for r in conn.execute('SELECT * FROM accounts ORDER BY uid')]
        self.assertEqual(after, before)
        public = self.client.get('/ui/accounts', headers=self.headers).text
        self.assertNotIn('token-one', public)

    def test_invalid_import_is_atomic_and_does_not_echo_secrets(self):
        records = [{'uid':'one','token':'secret-credential'}, {'uid':'bad','enabled':'false','token':'secret-credential'}]
        response = self.client.post('/ui/accounts/import', headers=self.headers, json={'accounts':records})
        self.assertEqual(response.status_code, 400)
        self.assertNotIn('secret-credential', response.text)
        with database.get_db() as conn:
            self.assertEqual(conn.execute('SELECT COUNT(*) FROM accounts').fetchone()[0], 0)

    def test_legacy_import_preserves_existing_metadata_and_identity(self):
        self.add('one', 0)
        response = self.client.post('/ui/accounts/batch-import', headers=self.headers,
                                    json={'accounts':[{'user_id':'one','token':'updated'}]})
        self.assertEqual(response.status_code, 200, response.text)
        with database.get_db() as conn:
            row = conn.execute('SELECT * FROM accounts WHERE uid=?', ('one',)).fetchone()
        self.assertEqual(row['security_oauth_token'], 'updated')
        self.assertEqual(row['machine_id'], 'machine-one')
        self.assertEqual(row['refresh_token'], 'refresh-one')
        self.assertEqual(row['remark'], '备注 one')
        self.assertEqual(row['enabled'], 0)

    def test_import_requires_auth_and_body_instead_of_scanning(self):
        self.assertEqual(self.client.post('/ui/accounts/import', json={'accounts':[]}).status_code, 401)
        self.assertEqual(self.client.post('/ui/accounts/import', headers=self.headers).status_code, 422)

    def enable_auto(self):
        response = self.client.post('/ui/accounts/scheduling', headers=self.headers, json={'enabled':True})
        self.assertEqual(response.status_code, 200, response.text)

    def test_scheduling_is_authenticated_and_boolean(self):
        self.assertEqual(self.client.post('/ui/accounts/scheduling', json={'enabled':True}).status_code, 401)
        self.assertEqual(self.client.post('/ui/accounts/scheduling', headers=self.headers, json={'enabled':'false'}).status_code, 400)
        self.enable_auto()
        self.assertTrue(self.client.get('/ui/accounts', headers=self.headers).json()['auto_schedule'])

    def test_auto_selects_credited_accounts_and_keeps_manual_selection(self):
        for uid in ['empty','shared','paid','unknown']: self.add(uid)
        self.add('disabled', 0)
        with database.get_db() as conn:
            conn.execute("INSERT INTO settings VALUES ('active_uid','empty')")
        self.enable_auto()
        observed = []
        def quota(uid):
            if uid=='unknown': return {'ok':False, 'uid':uid}
            return {'ok':True,'uid':uid,'quota':{'userQuota':{'remaining': 2 if uid=='paid' else 0}, 'orgResourcePackage':{'available':True,'remaining':5 if uid=='shared' else 0}}}
        async def complete(payload, sess):
            observed.append(sess.identity.uid)
            return {'choices':[{'message':{'content':'OK'}}]}
        with patch.object(tokens, 'get_account_quota', side_effect=quota) as fetch, patch.object(gateway, 'complete_openai_response', side_effect=complete):
            for _ in range(4):
                r=self.client.post('/v1/chat/completions',json={'model':'auto'})
                self.assertEqual(r.status_code,200,r.text)
            self.assertEqual(fetch.call_count,4)
        self.assertEqual(set(observed),{'shared','paid'})
        self.assertEqual(observed.count('shared'),2)
        with database.get_db() as conn:
            self.assertEqual(conn.execute("SELECT value FROM settings WHERE key='active_uid'").fetchone()[0],'empty')

    def test_auto_no_known_quota_returns_503_without_inference(self):
        self.add('empty'); self.enable_auto()
        with patch.object(tokens,'get_account_quota',return_value={'ok':True,'quota':{'isQuotaExceeded':True}}), patch.object(gateway,'complete_openai_response') as complete:
            response=self.client.post('/v1/chat/completions',json={'model':'auto'})
        self.assertEqual(response.status_code,503,response.text)
        complete.assert_not_called()

    def test_auto_retries_an_account_error_on_a_different_account(self):
        self.add('one'); self.add('two'); self.enable_auto()
        observed=[]
        async def complete(payload,sess):
            observed.append(sess.identity.uid)
            if len(observed)==1: raise RuntimeError('HTTP 403 forbidden')
            return {'choices':[{'message':{'content':'OK'}}]}
        with patch.object(tokens,'get_account_quota',return_value={'ok':True,'quota':{'userQuota':{'remaining':10}}}), patch.object(gateway,'complete_openai_response',side_effect=complete):
            response=self.client.post('/v1/chat/completions',json={'model':'auto'})
        self.assertEqual(response.status_code,200,response.text)
        self.assertEqual(len(set(observed)),2)

    def test_manual_mode_uses_selected_account_without_quota_lookup(self):
        self.add('one'); self.add('two')
        with database.get_db() as conn: conn.execute("INSERT INTO settings VALUES ('active_uid','two')")
        observed=[]
        async def complete(payload,sess):
            observed.append(sess.identity.uid)
            return {'choices':[{'message':{'content':'OK'}}]}
        with patch.object(tokens,'get_account_quota') as quota, patch.object(gateway,'complete_openai_response',side_effect=complete):
            response=self.client.post('/v1/chat/completions',json={'model':'auto'})
        self.assertEqual(response.status_code,200)
        self.assertEqual(observed,['two'])
        quota.assert_not_called()

    def test_import_rolls_back_when_later_row_fails_during_transaction(self):
        self.add('one')
        response = self.client.post('/ui/accounts/import', headers=self.headers, json={'accounts':[
            {'uid':'one','token':'replacement'}, {'uid':'two','token':'secret','machine_id':None}]})
        self.assertEqual(response.status_code, 400)
        with database.get_db() as conn:
            self.assertEqual(conn.execute('SELECT security_oauth_token FROM accounts WHERE uid=?', ('one',)).fetchone()[0], 'token-one')

    def test_scheduler_concurrency_cache_expiry_and_disabled_account(self):
        self.add('one'); self.add('two')
        with patch.object(tokens, 'get_account_quota', return_value={'ok':True,'quota':{'userQuota':{'remaining':10}}}) as quota:
            with ThreadPoolExecutor(max_workers=4) as pool:
                selected = list(pool.map(lambda _: scheduler.select_auto_session().identity.uid, range(8)))
            self.assertEqual(selected.count('one'), 4)
            self.assertEqual(selected.count('two'), 4)
            self.assertEqual(quota.call_count, 2)
            with database.get_db() as conn:
                conn.execute("UPDATE accounts SET enabled=0 WHERE uid='one'")
            self.assertEqual(scheduler.select_auto_session().identity.uid, 'two')
            with patch.object(scheduler.time, 'monotonic', return_value=scheduler.time.monotonic()+61):
                scheduler.select_auto_session()
            self.assertEqual(quota.call_count, 3)
            with database.get_db() as conn:
                conn.execute("UPDATE accounts SET security_oauth_token='new-token' WHERE uid='two'")
            scheduler.select_auto_session()
            self.assertEqual(quota.call_count, 4)

    def test_automatic_mode_does_not_change_manual_selection_from_status(self):
        self.add('one'); self.enable_auto()
        self.assertTrue(self.client.get('/ui/status', headers=self.headers).json()['ready'])
        self.assertEqual(self.client.post('/ui/accounts/select', headers=self.headers, json={'uid':'one'}).status_code, 409)
        with database.get_db() as conn:
            self.assertIsNone(conn.execute("SELECT value FROM settings WHERE key='active_uid'").fetchone())

    def test_confirmed_quota_exhaustion_retries_but_transient_network_error_does_not(self):
        self.add('one'); self.add('two'); self.enable_auto()
        observed = []
        async def complete(payload, sess):
            observed.append(sess.identity.uid)
            if len(observed) == 1: raise RuntimeError('HTTP 429 quota exceeded')
            return {'choices':[]}
        with patch.object(tokens, 'get_account_quota', return_value={'ok':True,'quota':{'userQuota':{'remaining':10}}}), patch.object(gateway, 'get_account_quota', return_value={'ok':True,'quota':{'isQuotaExceeded':True}}), patch.object(gateway, 'complete_openai_response', side_effect=complete):
            self.assertEqual(self.client.post('/v1/chat/completions', json={}).status_code, 200)
        self.assertEqual(len(set(observed)), 2)
        scheduler.invalidate_quota()
        with patch.object(tokens, 'get_account_quota', return_value={'ok':True,'quota':{'userQuota':{'remaining':10}}}), patch.object(gateway, 'complete_openai_response', side_effect=RuntimeError('connection failed')) as inference:
            self.assertEqual(self.client.post('/v1/chat/completions', json={}).status_code, 502)
            self.assertEqual(inference.call_count, 1)

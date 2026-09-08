import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from qoder2api import app as gateway

class ModelListTests(unittest.TestCase):
    def test_requires_same_api_key_as_completions(self):
        with patch.object(gateway, 'load_config', return_value={'auth_required': True, 'allowed_keys': ['test-key']}):
            client = TestClient(gateway.app)
            self.assertEqual(client.get('/v1/models').status_code, 401)
            self.assertEqual(client.get('/v1/models', headers={'Authorization': 'Bearer wrong'}).status_code, 401)
            response = client.get('/v1/models', headers={'Authorization': 'Bearer test-key'})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()['object'], 'list')
            ids = [model['id'] for model in response.json()['data']]
            self.assertIn('qmodel_38max', ids)
            self.assertIn('kmodel_latest', ids)
            self.assertEqual(len(ids), len(set(ids)))
            for model in response.json()['data']:
                self.assertEqual(model['object'], 'model')
                self.assertIn('created', model)
                self.assertIn('owned_by', model)
                self.assertNotIn('api_key', model)

    def test_allows_access_when_gateway_auth_disabled(self):
        with patch.object(gateway, 'load_config', return_value={'auth_required': False}):
            self.assertEqual(TestClient(gateway.app).get('/v1/models').status_code, 200)

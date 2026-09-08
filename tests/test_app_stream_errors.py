import unittest
from types import SimpleNamespace
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from qoder2api import app as gateway

class StreamErrorTests(unittest.TestCase):
    def request_with_stream(self, stream):
        session = SimpleNamespace(identity=SimpleNamespace(name='test', uid='test'))
        with patch.object(gateway, 'load_config', return_value={'auth_required': False}), \
             patch.object(gateway, 'db_load_accounts', return_value={'accounts': [{'enabled': True}]}), \
             patch.object(gateway, 'get_session', AsyncMock(return_value=session)), \
             patch.object(gateway, 'stream_openai_response', stream):
            return TestClient(gateway.app).post('/v1/chat/completions', json={'model': 'lite', 'stream': True})

    def test_error_before_first_chunk_is_http_error(self):
        async def fail(*args):
            raise RuntimeError('Unsupported model')
            yield
        response = self.request_with_stream(fail)
        self.assertEqual(response.status_code, 502)
        self.assertIn('Unsupported model', response.text)

    def test_error_after_first_chunk_is_sse_error(self):
        async def fail(*args):
            yield 'data: {"choices":[{"delta":{"content":"hello"}}]}\n\n'
            raise RuntimeError('connection failed')
        response = self.request_with_stream(fail)
        self.assertIn('"error"', response.text)
        self.assertIn('connection failed', response.text)
        self.assertNotIn('[DONE]', response.text)

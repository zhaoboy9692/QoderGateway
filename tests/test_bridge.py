import unittest,json
from types import SimpleNamespace
from unittest.mock import patch
from qoder2api import bridge
S=SimpleNamespace(identity=SimpleNamespace(user_type='personal_standard'))
class BridgeTests(unittest.IsolatedAsyncioTestCase):
 def test_error_event_rejected(self):
  with self.assertRaisesRegex(RuntimeError,'Unsupported model'):
   bridge.extract_delta(json.dumps({'code':'invalid_model_error','message':'Unsupported model x','type':'invalid_model_error'}))
 def test_unknown_model_rejected_before_upstream_fallback(self):
  with self.assertRaisesRegex(RuntimeError,"Unsupported model"):
   bridge.build_qoder_body({"model":"no-such-model-codex-validation"},S)
 def test_image_preserved(self):
  parts=[{'type':'text','text':'describe'},{'type':'image_url','image_url':{'url':'data:image/png;base64,AAAA'}}]
  b,_,_=bridge.build_qoder_body({'model':'qmodel_38max','messages':[{'role':'user','content':parts}],'max_tokens':512},S)
  self.assertEqual(b['messages'][-1].get('contents'),parts)
  self.assertEqual(b.get('model_config',{}).get('key'),'qmodel_38max')
  self.assertEqual(b.get('parameters',{}).get('max_tokens'),512)
 async def test_empty_stream_rejected(self):
  async def empty(*a):
   yield 'data: [DONE]'
  with patch.object(bridge,'qoder_stream_lines',empty):
   with self.assertRaisesRegex(RuntimeError,'empty'):
    _=[x async for x in bridge.stream_openai_response({'model':'lite'},S)]
   with self.assertRaisesRegex(RuntimeError,'empty'):
    await bridge.complete_openai_response({'model':'lite'},S)
 async def test_legacy_text(self):
  async def fake(*a):
   yield 'data: '+json.dumps({'body':json.dumps({'choices':[{'delta':{'content':'hello'}}]})})
  with patch.object(bridge,'qoder_stream_lines',fake):
   r=await bridge.complete_openai_response({'model':'lite'},S)
   self.assertEqual(r['choices'][0]['message']['content'],'hello')
if __name__=='__main__':unittest.main()

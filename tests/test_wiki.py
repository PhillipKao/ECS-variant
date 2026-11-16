from copy import deepcopy
import http.client
import json
from pathlib import Path
import shutil
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import build
import serve

ROOT = Path(__file__).resolve().parents[1]

class WikiTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        for name in ('data', 'assets'):
            shutil.copytree(ROOT / name, self.root / name)
        shutil.copy(ROOT / 'template.html', self.root / 'template.html')
        self.patches = [patch.object(build,'ROOT',self.root),patch.object(serve,'ROOT',self.root)]
        for p in self.patches:p.start()
        self.addCleanup(self.tmp.cleanup)
        for p in self.patches:self.addCleanup(p.stop)
        self.variants=build.load('variants')
        self.payload=dict(accession='VCV000017023',date='2026-11-16',classification='Uncertain significance',scope='隔離測試',note='<script>僅供測試</script>\n證據',record_id='test-one')
    def test_append_duplicate_order_and_classification_change(self):
        labs,added=serve.append_record(self.variants,[],self.payload)
        self.assertTrue(added)
        again,added=serve.append_record(self.variants,labs,self.payload)
        self.assertFalse(added);self.assertEqual(labs,again)
        second={**self.payload,'record_id':'test-two','classification':'Pathogenic','note':'第二次測試'}
        updated,added=serve.append_record(self.variants,labs,second)
        self.assertEqual([s['revision'] for s in updated[0]['history']],[1,2])
        self.assertEqual(labs[0]['history'][0],updated[0]['history'][0])
        self.assertIn('Uncertain significance → Pathogenic',build.lab_history(updated[0]['history']))
        self.assertIn('&lt;script&gt;',build.lab_history(updated[0]['history']))
        with self.assertRaises(ValueError):serve.append_record(self.variants,updated,{**second,'record_id':'third','date':'2026-11-15'})
        with self.assertRaises(ValueError):serve.append_record(self.variants,updated,{**second,'record_id':'fourth','note':' '})
    def test_build_no_demo_and_sources(self):
        build.main();html=(self.root/'index.html').read_text()
        self.assertEqual(html.count('class="variant"'),4)
        self.assertNotIn('DEMO-A',html)
        for v in self.variants:
            self.assertIn(v['accession'],html)
            self.assertTrue(v['explanation']['sources'])
        self.assertNotIn('<!-- RECORDS -->',html)
    def test_http_save_reload_duplicate_reject_and_rollback(self):
        build.main()
        server=serve.ThreadingHTTPServer(('127.0.0.1',0),serve.Handler)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        self.addCleanup(server.server_close);self.addCleanup(server.shutdown)
        def request(method,path,body=None,headers=None):
            connection=http.client.HTTPConnection('127.0.0.1',server.server_port)
            connection.request(method,path,body,headers or {})
            response=connection.getresponse();data=response.read();connection.close();return response.status,data
        status,data=request('GET','/api/state');self.assertEqual(status,200)
        token=json.loads(data)['token']
        headers={'Content-Type':'application/json','X-Wiki-Token':token}
        status,data=request('POST','/api/lab',json.dumps(self.payload),headers);self.assertEqual(status,200)
        self.assertTrue(json.loads(data)['added'])
        status,page=request('GET','/');self.assertEqual(status,200);self.assertIn('隔離測試',page.decode())
        status,data=request('GET','/api/state');self.assertEqual(len(json.loads(data)['labs'][0]['history']),1)
        status,data=request('POST','/api/lab',json.dumps(self.payload),headers);self.assertFalse(json.loads(data)['added'])
        status,_=request('POST','/api/lab',json.dumps(self.payload),{'Content-Type':'application/json'});self.assertEqual(status,403)
        status,_=request('POST','/api/lab',json.dumps(self.payload),{**headers,'Origin':'https://example.com'});self.assertEqual(status,403)
        status,_=request('GET','/data/lab.json');self.assertEqual(status,404)
        original=(self.root/'data/lab.json').read_bytes()
        with patch.object(build,'main',side_effect=RuntimeError('test failure')):
            status,_=request('POST','/api/lab',json.dumps({**self.payload,'record_id':'rollback','note':'回滾測試'}),headers)
        self.assertEqual(status,500);self.assertEqual((self.root/'data/lab.json').read_bytes(),original)

if __name__=='__main__':unittest.main()

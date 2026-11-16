"""Local-only editor: python3 scripts/serve.py (standard library only)."""
import argparse
import re
from copy import deepcopy
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import secrets
import threading
from urllib.parse import urlsplit
from datetime import date
import build

ROOT = build.ROOT
TOKEN = secrets.token_urlsafe(32)
LOCK = threading.Lock()

def append_record(variants, labs, payload):
    acc = payload['accession']
    variant = next((v for v in variants if v['accession'] == acc), None)
    if variant is None:
        gene = payload.get('gene', '').strip().upper()
        transcript = payload.get('transcript', '').strip()
        hgvs = payload.get('hgvs', '').strip()
        local_id = 'LAB:' + '|'.join((gene, transcript, hgvs))
        pending_id = 'LAB:' + '|'.join((gene, '', hgvs))
        if not gene or not hgvs or not (acc in (local_id, pending_id) or re.fullmatch(r'VCV\d{9}', acc)):
            raise ValueError('位點識別資料不完整')
        variant = dict(accession=acc, gene=gene, transcript=transcript, hgvs=hgvs, protein=payload.get('protein', ''))
    fields = {}
    for key in ('date', 'classification', 'scope', 'note', 'record_id'):
        value = payload.get(key)
        if not isinstance(value, str) or not value.strip():
            raise ValueError('日期、分類、範圍與判讀原因皆必填')
        fields[key] = value.strip()
    if re.fullmatch(r'VCV\d+\.\d+', payload.get('clinvar_version', '')):
        fields['clinvar_version'] = payload['clinvar_version']
    date.fromisoformat(fields['date'])
    if len(fields['classification']) > 200:
        raise ValueError('判讀結果過長')
    if len(fields['note']) > 12000 or len(fields['record_id']) > 100:
        raise ValueError('輸入內容過長')
    updated = deepcopy(labs)
    lab = next((x for x in updated if x['accession'] == acc), None)
    for item in updated:
        for snap in item['history']:
            if snap.get('record_id') == fields['record_id']:
                if item['accession'] != acc or any(snap[k] != fields[k] for k in ('date','classification','scope','note')):
                    raise ValueError('紀錄識別碼已用於其他內容')
                return updated, False
    if lab is not None and not lab['transcript'] and variant['transcript']:
        lab.update(transcript=variant['transcript'], protein=variant['protein'])
    if lab is None:
        lab = {k:variant[k] for k in ('gene','transcript','hgvs','protein','accession')}
        lab['history'] = []
        updated.append(lab)
    if any(all(h[k] == fields[k] for k in ('date','classification','scope','note')) for h in lab['history']):
        return updated, False
    if lab['history'] and fields['date'] < lab['history'][-1]['date']:
        raise ValueError('判讀日期早於最近一次紀錄，請依時間追加')
    fields['revision'] = lab['history'][-1]['revision']+1 if lab['history'] else 1
    lab['history'].append(fields)
    build.validate(variants, updated)
    return updated, True

class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)
    def json_response(self, status, data):
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(body)
    def allowed_host(self):
        return self.headers.get('Host') == f'127.0.0.1:{self.server.server_port}'
    def do_GET(self):
        if not self.allowed_host():
            return self.json_response(403, {'error':'只接受本機編輯器網址'})
        path = urlsplit(self.path).path
        if path == '/api/state':
            with LOCK:
                return self.json_response(200, {'token':TOKEN, 'labs':build.load('lab')})
        if path not in ('/', '/index.html') and not (path.startswith('/assets/') and '..' not in path):
            return self.send_error(404)
        if path.startswith('/assets/'):
            resolved = Path(self.translate_path(path)).resolve()
            if not resolved.is_relative_to((ROOT / 'assets').resolve()):
                return self.send_error(404)
        super().do_GET()
    def do_POST(self):
        expected_origin = f'http://127.0.0.1:{self.server.server_port}'
        if not self.allowed_host() or self.headers.get('Origin', expected_origin) != expected_origin or self.headers.get('X-Wiki-Token') != TOKEN:
            return self.json_response(403, {'error':'請從本機編輯器重新開啟頁面'})
        if self.path != '/api/lab':
            return self.json_response(404, {'error':'未知操作'})
        if self.headers.get('Content-Type') != 'application/json':
            return self.json_response(415, {'error':'僅支援 JSON'})
        try:
            size = int(self.headers.get('Content-Length', '0'))
            if not 0 < size <= 100000:
                raise ValueError('資料大小無效')
            payload = json.loads(self.rfile.read(size))
            with LOCK:
                variants, labs = build.load('variants'), build.load('lab')
                updated, added = append_record(variants, labs, payload)
                if added:
                    target = ROOT / 'data' / 'lab.json'
                    old = target.read_bytes()
                    temp = target.with_suffix('.json.tmp')
                    try:
                        temp.write_text(json.dumps(updated,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
                        temp.replace(target)
                        build.main()
                    except Exception:
                        temp.write_bytes(old)
                        temp.replace(target)
                        raise
                self.json_response(200, {'labs':updated, 'added':added})
        except (ValueError, KeyError, TypeError) as error:
            self.json_response(400, {'error':str(error)})
        except Exception:
            self.json_response(500, {'error':'未完成儲存，原資料已保留，請檢查本機檔案權限與資料格式'})

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8765)
    args = parser.parse_args()
    build.main()
    server = ThreadingHTTPServer(('127.0.0.1',args.port), Handler)
    print(f'本機判讀編輯器：http://127.0.0.1:{server.server_port}', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()

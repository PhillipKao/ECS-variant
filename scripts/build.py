"""Validate ClinVar snapshots and laboratory history, then build the offline wiki."""
from datetime import date
from html import escape
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
LAB_CLASSES = ('Pathogenic', 'Likely pathogenic', 'Uncertain significance', 'Likely benign', 'Benign')

def load(name):
    return json.loads((ROOT / 'data' / f'{name}.json').read_text(encoding='utf-8'))

def validate(variants, labs):
    identities = {}
    for item in variants:
        acc = item['accession']
        if not re.fullmatch(r'VCV\d{9}', acc) or acc in identities:
            raise ValueError(f'Invalid or duplicate accession: {acc}')
        if not all(item[k].strip() for k in ('gene', 'transcript', 'hgvs')):
            raise ValueError(f'Missing identity: {acc}')
        identities[acc] = item
        if not item['history']:
            raise ValueError(f'Missing ClinVar history: {acc}')
        previous = None
        for snap in item['history']:
            date.fromisoformat(snap['date'])
            if type(snap['version']) is not int or snap['version'] < 1:
                raise ValueError(f'Invalid VCV version: {acc}')
            if not all(snap[k].strip() for k in ('classification', 'review', 'scope', 'note')):
                raise ValueError(f'Incomplete ClinVar snapshot: {acc}')
            if previous and (snap['version'] <= previous['version'] or snap['date'] < previous['date']):
                raise ValueError(f'Unordered ClinVar history: {acc}')
            previous = snap
        explanation = item.get('explanation')
        if explanation:
            date.fromisoformat(explanation['checked_on'])
            if not all(explanation[k].strip() for k in ('summary', 'impact', 'context')):
                raise ValueError(f'Incomplete explanation: {acc}')
            for source in explanation['sources']:
                if not source['url'].startswith('https://') or not source['title'].strip():
                    raise ValueError('Invalid explanation source')
    seen, requests = set(), set()
    for item in labs:
        acc = item['accession']
        if acc in seen or (acc not in identities and not ((acc.startswith('LAB:') or re.fullmatch(r'VCV\d{9}',acc)) and all(item[k].strip() for k in ('gene','hgvs')))):
            raise ValueError(f'Laboratory variant must match one existing VCV: {acc}')
        seen.add(acc)
        for key in ('gene', 'transcript', 'hgvs', 'protein'):
            if acc in identities and item[key] != identities[acc][key]:
                raise ValueError(f'Laboratory identity mismatch: {acc}')
        previous = None
        if not item['history']:
            raise ValueError('Empty laboratory history')
        for snap in item['history']:
            date.fromisoformat(snap['date'])
            if type(snap['revision']) is not int or snap['revision'] < 1:
                raise ValueError('Invalid laboratory revision')
            if not all(snap[k].strip() for k in ('classification', 'scope', 'note')):
                raise ValueError('Incomplete laboratory interpretation')
            if previous and (snap['revision'] <= previous['revision'] or snap['date'] < previous['date']):
                raise ValueError('實驗室紀錄須依日期追加，且序號遞增')
            rid = snap.get('record_id')
            if rid:
                if rid in requests:
                    raise ValueError('Duplicate laboratory record ID')
                requests.add(rid)
            previous = snap

def badge(label):
    color = 'red' if label in ('Pathogenic', 'Likely pathogenic') else 'green' if label in ('Benign', 'Likely benign') else 'amber'
    return f'<span class="badge {color}">{escape(label)}</span>'

def lab_history(history):
    if not history:
        return '<p class="empty">尚無實驗室判讀。可在右側表單新增第一筆紀錄。</p>'
    rows = []
    previous = None
    for snap in history:
        change = '首次判讀' if previous is None else ('分類維持不變' if previous['classification'] == snap['classification'] else previous['classification'] + ' → ' + snap['classification'])
        rows.append(f'<section class="event"><small>{escape(snap["date"])} · 第 {snap["revision"]} 筆</small><h4>{escape(change)}</h4>{badge(snap["classification"])}<p class="multiline">{escape(snap["note"])}</p><small>{escape(snap["scope"])}</small></section>')
        previous = snap
    return ''.join(reversed(rows))

def record(item, labs):
    acc = item['accession']
    latest = item['history'][-1]
    lab = next((x['history'] for x in labs if x['accession'] == acc), [])
    rows, previous = [], None
    for snap in item['history']:
        ident = f'{acc}.{snap["version"]}'
        change = '首次收錄' if previous is None else ('分類維持不變' if previous['classification'] == snap['classification'] else previous['classification'] + ' → ' + snap['classification'])
        rows.append(f'<section class="event"><small>收錄 {escape(snap["date"])} · <a href="https://www.ncbi.nlm.nih.gov/clinvar/variation/{ident}/" target="_blank" rel="noopener">{ident} ↗</a></small><h4>{escape(change)}</h4>{badge(snap["classification"])}<p>{escape(snap["note"])}</p><small>{escape(snap["scope"])}<br>{escape(snap["review"])}</small></section>')
        previous = snap
    explanation = item.get('explanation')
    desc = ''
    if explanation:
        links = ' · '.join(f'<a href="{escape(s["url"], quote=True)}" target="_blank" rel="noopener">{escape(s["title"])}</a>' for s in explanation['sources'])
        desc = f'<div class="explanation"><h3>中文解讀與可能影響</h3><p>{escape(explanation["summary"])}</p><div class="impact"><b>可能影響</b><p>{escape(explanation["impact"])}</p></div><p class="context">{escape(explanation["context"])}</p><small>說明查核：{escape(explanation["checked_on"])} · {links}</small></div>'
    return (f'<details class="variant" data-accession="{acc}"><summary><span class="gene">{escape(item["gene"])}</span><span class="variant-id"><strong>{escape(item["hgvs"])}</strong><small>{escape(item["transcript"])} · {escape(item["protein"]) or "蛋白標記未提供"}<br>{acc}</small></span><span class="summary-class">{badge(latest["classification"])}<small>ClinVar · v{latest["version"]}</small></span></summary>'
            f'<div class="variant-body">{desc}<div class="comparison"><div><small>CLINVAR 最近收錄</small>{badge(latest["classification"])}<small>{escape(latest["date"])}</small></div><div><small>實驗室最近判讀</small><div data-lab-latest>{badge(lab[-1]["classification"]) if lab else "尚未判讀"}</div></div></div>'
            f'<div class="timelines"><div><h3>ClinVar 收錄歷程 <span>{len(rows)}</span></h3>{"".join(reversed(rows))}</div><div><div class="lab-heading"><h3>實驗室判讀歷程</h3><button type="button" class="text-button add-lab" data-target="{acc}">＋ 新增判讀</button></div><div data-lab-history>{lab_history(lab)}</div></div></div></div></details>')

def main():
    variants, labs = load('variants'), load('lab')
    validate(variants, labs)
    state = json.dumps({'variants': variants, 'labs': labs, 'archive': load('archive') if (ROOT / 'data/archive.json').exists() else []}, ensure_ascii=False).replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')
    template = (ROOT / 'template.html').read_text(encoding='utf-8')
    if template.count('<!-- RECORDS -->') != 1 or template.count('<!-- STATE -->') != 1:
        raise ValueError('Missing or duplicate template insertion point')
    output = template.replace('<!-- RECORDS -->', '\n'.join(record(v, labs) for v in variants)).replace('<!-- STATE -->', f'<script id="wiki-state" type="application/json">{state}</script>')
    temp = ROOT / 'index.html.tmp'
    temp.write_text(output, encoding='utf-8')
    temp.replace(ROOT / 'index.html')

if __name__ == '__main__':
    main()

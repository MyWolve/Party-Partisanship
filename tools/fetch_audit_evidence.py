"""Explicit network step for the 2026 audit; analysis itself is offline.

Run from the repository root. Existing snapshots are never overwritten.
"""
import hashlib
import json
import time
from datetime import date
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
CASES = {'38-1': [159], '39-1': [166], '39-2': [57], '40-3': [12],
         '41-1': [208, 351, 425, 699, 742, 748, 752],
         '42-1': [71, 106, 136, 150, 175, 713, 723, 724, 725, 871, 872]}


def validate_content(name, data):
    if name.endswith('.pdf') and not data.startswith(b'%PDF-'):
        raise ValueError(f'Expected a PDF, received different content: {name}')
    if name.endswith('.xml'):
        from xml.etree import ElementTree
        root = ElementTree.fromstring(data)
        if root.tag.lower().endswith('html'):
            raise ValueError(f'Expected vote XML, received HTML: {name}')


def main():
    dest = ROOT / 'evidence'
    dest.mkdir(exist_ok=True)
    manifest = dest / 'sources.json'
    records = json.loads(manifest.read_text(encoding='utf-8')) if manifest.exists() else {}
    urls = {f'{s}-{n}.xml': f'https://www.ourcommons.ca/members/en/votes/{s.replace("-", "/")}/{n}/xml'
            for s, numbers in CASES.items() for n in numbers}
    urls['42-1-871-journals.html'] = 'https://www.ourcommons.ca/documentviewer/en/42-1/house/sitting-317/journals'
    urls['42-1-724-journals.html'] = 'https://www.ourcommons.ca/documentviewer/en/42-1/house/sitting-308/journals'
    designations = json.loads((ROOT / 'audit/whip_designations.json').read_text(encoding='utf-8'))
    for url in sorted({u for rule in designations for u in rule['sources']}):
        extension = '.pdf' if url.lower().endswith('.pdf') else '.html'
        urls['whip-' + hashlib.sha256(url.encode()).hexdigest()[:12] + extension] = url
    for name, url in urls.items():
        path = dest / name
        if name in records and records[name]['url'] != url:
            raise ValueError(f'Snapshot URL changed for {name}')
        if not path.exists():
            time.sleep(0.5)
            session = requests.Session()
            response = session.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=45)
            response.raise_for_status()
            # Government Publications uses a cookie-backed archive interstitial.
            if name.endswith('.pdf') and '/site/archivee-archived.html' in response.url:
                response = session.get(url, headers={'Referer': response.url}, timeout=45)
                response.raise_for_status()
            validate_content(name, response.content)
            if name in records and hashlib.sha256(response.content).hexdigest() != records[name]['sha256']:
                raise ValueError(f'Remote source changed; review required: {name}')
            path.write_bytes(response.content)
        data = path.read_bytes()
        validate_content(name, data)
        sha = hashlib.sha256(data).hexdigest()
        if name in records and records[name]['sha256'] != sha:
            raise ValueError(f'Local snapshot changed; review required: {name}')
        if name not in records:
            records[name] = {'url': url, 'retrieved_date': date.today().isoformat(), 'sha256': sha}
        manifest.write_text(json.dumps(records, indent=2, sort_keys=True) + '\n', encoding='utf-8')
        print(name, path.stat().st_size, flush=True)


if __name__ == '__main__':
    main()

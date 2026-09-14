"""Collect an explicit session into a NEW review snapshot, never the frozen corpus.

python can_scrape.py --session 40-1 --output incoming/40-1-review
A failed collection retains responses and a failed manifest for diagnosis.
No snapshot is automatically promoted to the analytical corpus.
"""
import argparse
import csv
import hashlib
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
import xml.etree.ElementTree as ET

import requests
from vote_data import parse_vote_text, tally

BASE_URL = 'https://www.ourcommons.ca'
HEADERS = {'User-Agent': 'Party-Partisanship research collector', 'Accept-Language': 'en-CA,en;q=0.9'}
REQUEST_DELAY_SECONDS = 0.5
METADATA_FIELDS = [
    ('vote_number', ('decisiondivisionnumber',)),
    ('date', ('decisioneventdatetime', 'decisiondivisiondatetime')),
    ('subject', ('decisiondivisionsubject',)),
    ('bill_number', ('billnumbercode',)),
    ('result', ('decisionresultname',)),
    ('yeas', ('decisiondivisionnumberofyeas',)),
    ('nays', ('decisiondivisionnumberofnays',)),
    ('paired', ('decisiondivisionnumberofpaired',)),
]


def fetch(url):
    """Bounded, polite GET; transport errors propagate as collection failures."""
    time.sleep(REQUEST_DELAY_SECONDS)
    response = requests.get(url, headers=HEADERS, timeout=45)
    response.raise_for_status()
    return response


def extract_field(element, tags):
    matches = [child for child in element.iter()
               if child.tag.rsplit('}', 1)[-1].lower() in tags]
    if len(matches) > 1:
        raise ValueError(f'Ambiguous metadata field {tags}')
    return (matches[0].text or '').strip() if matches else ''


def parse_metadata(data):
    root = ET.fromstring(data)
    if root.tag.rsplit('}', 1)[-1].lower() == 'html':
        raise ValueError('HTML received instead of session XML')
    votes, seen = [], set()
    for entry in root:
        row = {key: extract_field(entry, tags) for key, tags in METADATA_FIELDS}
        number = row['vote_number']
        if not re.fullmatch(r'[1-9]\d*', number) or number in seen:
            raise ValueError(f'Invalid or duplicate division: {number!r}')
        seen.add(number)
        datetime.fromisoformat(row['date'])
        if not row['subject'] or not row['result']:
            raise ValueError(f'Missing subject/result in division {number}')
        for key in ('yeas', 'nays', 'paired'):
            if not re.fullmatch(r'\d+', row[key]):
                raise ValueError(f'Invalid {key} in division {number}')
        votes.append(row)
    if not votes:
        raise ValueError('Empty session export; completeness cannot be established')
    return sorted(votes, key=lambda row: int(row['vote_number']))


def collect_session(session, output):
    if not re.fullmatch(r'[1-9]\d*-[1-9]\d*', session):
        raise ValueError('Session must be parliament-session, e.g. 40-1')
    output = Path(output).resolve()
    # An exclusive directory claim prevents overwrite and unsafe implicit resume.
    output.mkdir(parents=True, exist_ok=False)
    manifest = {'session': session, 'status': 'collecting', 'responses': [],
                'started_utc': datetime.now(timezone.utc).isoformat(),
                'note': 'Separate raw snapshot; no audit overlays or corpus promotion.'}
    def save_manifest():
        (output/'collection_manifest.json').write_text(json.dumps(manifest, indent=2)+'\n', encoding='utf-8')
    def download(url, relative):
        response = fetch(url)
        path = output/relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(response.content)
        manifest['responses'].append({'requested_url': url, 'resolved_url': response.url,
            'retrieved_utc': datetime.now(timezone.utc).isoformat(), 'path': relative,
            'http_status': response.status_code, 'content_type': response.headers.get('Content-Type', ''),
            'bytes': len(response.content), 'sha256': hashlib.sha256(response.content).hexdigest()})
        save_manifest()
        return response.content
    save_manifest()
    try:
        url = f'{BASE_URL}/members/en/votes/xml?parlSession={session}'
        data = download(url, 'session-before.xml')
        votes = parse_metadata(data)
        directory = output/f'Parliament_{session}'
        directory.mkdir()
        with (directory/'votes_metadata.csv').open('w', newline='', encoding='utf-8') as stream:
            writer = csv.DictWriter(stream, fieldnames=[key for key, _ in METADATA_FIELDS], lineterminator='\n')
            writer.writeheader(); writer.writerows(votes)
        parliament, sitting = session.split('-')
        for vote in votes:
            number = vote['vote_number']
            data = download(f'{BASE_URL}/members/en/votes/{parliament}/{sitting}/{number}/csv',
                            f'Parliament_{session}/file_{number}.csv')
            rows = parse_vote_text(data.decode('utf-8-sig'))
            if not rows or tally(rows) != tuple(int(vote[k]) for k in ('yeas', 'nays', 'paired')):
                raise ValueError(f'Division {number}: empty or mismatched raw tally; source audit required')
        # Detect a changing session during the run, rather than mixing snapshots.
        after = parse_metadata(download(url, 'session-after.xml'))
        if votes != after:
            raise ValueError('Session metadata changed during collection; collect a new snapshot')
        manifest.update(status='validated_raw_snapshot', divisions=len(votes))
    except Exception as error:
        manifest.update(status='failed', error=f'{type(error).__name__}: {error}')
        raise
    finally:
        manifest['finished_utc'] = datetime.now(timezone.utc).isoformat()
        save_manifest()
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session', required=True)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    try:
        result = collect_session(args.session, args.output)
    except (OSError, ValueError, ET.ParseError, requests.RequestException) as error:
        parser.exit(1, f'Collection failed: {error}\n')
    print(f"{result['status']}: {result['divisions']} divisions; inspect before any corpus update")


if __name__ == '__main__':
    main()

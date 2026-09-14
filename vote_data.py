"""Strict CSV parsing and explicit, checksum-bound audit corrections.

No plotting or network dependencies. Original exports are never rewritten.
Yea/Nay means the record contains both flags; binary metrics exclude it.
"""
import csv
import hashlib
import io
import json
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DECISIONS = ROOT / 'audit' / 'data_decisions.json'


def text_hash(text):
    """Portable text digest: normalize line endings only (not content/BOM)."""
    return hashlib.sha256(text.replace('\r\n', '\n').encode('utf-8')).hexdigest()


@lru_cache(maxsize=1)
def decisions():
    return json.loads(DECISIONS.read_text(encoding='utf-8'))


def parse_vote_text(text):
    reader = csv.DictReader(io.StringIO(text.lstrip('\ufeff')))
    fields = reader.fieldnames or []
    def column(*names):
        found = [n for n in names if n in fields]
        if len(found) != 1:
            raise ValueError(f'Expected one of {names}; got {fields}')
        return found[0]
    member = column('Member of Parliament', 'Member')
    party = column('Political Affiliation', 'Affiliation', 'Political Party')
    vote = column('Member Voted', 'Voted')
    paired = column('Paired')
    if len(fields) != len(set(fields)):
        raise ValueError('Duplicate CSV column')
    result, seen = [], set()
    for line, row in enumerate(reader, 2):
        if None in row or any(v is None for v in row.values()):
            raise ValueError(f'Malformed CSV row {line}')
        if not row[member].strip() or not row[party].strip():
            raise ValueError(f'Missing member or party at row {line}')
        if row[vote] not in ('Yea', 'Nay', 'Yea/Nay', '') or row[paired] not in ('', 'Paired'):
            raise ValueError(f'Unrecognized vote/paired value at row {line}')
        if row[vote] == '' and row[paired] != 'Paired':
            raise ValueError(f'Unobservable row without paired flag at row {line}')
        key = row.get('Person ID') or row[member]
        if key in seen:
            raise ValueError(f'Duplicate member {key}')
        seen.add(key)
        result.append({'member_id': row.get('Person ID', ''), 'member': row[member],
                       'party': row[party], 'vote': row[vote], 'paired': row[paired] == 'Paired'})
    return result


def read_vote_rows(file_path, apply_audit=True):
    path = Path(file_path)
    text = path.read_text(encoding='utf-8')
    rows = parse_vote_text(text)
    key = f'{path.parent.name.replace("Parliament_", "")}/{path.stem.replace("file_", "")}'
    decision = decisions().get(key) if apply_audit else None
    if decision:
        if text_hash(text) != decision['raw_sha256']:
            raise ValueError(f'{key}: audited raw file changed; re-audit required')
        for row in rows:
            if row['member_id'] in decision.get('dual_member_ids', []):
                row['vote'] = 'Yea/Nay'
        if 'replacement' in decision:
            replacement = ROOT / decision['replacement']
            data = replacement.read_text(encoding='utf-8')
            if text_hash(data) != decision['replacement_sha256']:
                raise ValueError(f'{key}: derived replacement changed')
            rows = parse_vote_text(data)
        rows.extend(decision.get('append_rows', []))
    return rows


def apply_metadata_decision(session, row):
    decision = decisions().get(f'{session}/{int(row["vote_number"])}')
    if decision:
        if row != decision['raw_metadata']:
            raise ValueError(f'{session}/{row["vote_number"]}: audited metadata changed')
        return {**row, **decision.get('metadata_override', {})}
    return row


def tally(rows):
    """Official flag totals; one dual-coded member contributes to each side."""
    return (sum(r['vote'] in ('Yea', 'Yea/Nay') for r in rows),
            sum(r['vote'] in ('Nay', 'Yea/Nay') for r in rows),
            sum(r['paired'] for r in rows))


def binary_vote(row):
    """Only unpaired, single-sided votes enter cohesion and dissent metrics."""
    return row['vote'] if not row['paired'] and row['vote'] in ('Yea', 'Nay') else ''

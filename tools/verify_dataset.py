"""Read exported CSVs independently and reconcile them with E1's division audit."""
import argparse
from collections import defaultdict
import csv
import gzip
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from provenance import digest


def verify(dataset, classification):
    dataset = Path(dataset)
    manifest = json.loads((dataset/'manifest.json').read_text(encoding='utf-8'))
    for name, expected in manifest['files'].items():
        if digest(dataset/name) != expected:
            raise ValueError(f'Export hash mismatch: {name}')
    with (dataset/'divisions.csv').open(encoding='utf-8', newline='') as handle:
        divisions = {}
        for r in csv.DictReader(handle):
            key = r['session'], int(r['division'])
            if key in divisions:
                raise ValueError('Duplicate exported division')
            divisions[key] = r
    totals, parties = defaultdict(lambda: [0, 0, 0]), defaultdict(lambda: [0, 0])
    counts = defaultdict(int)
    previous, seen = None, set()
    with gzip.open(dataset/'members.csv.gz', 'rt', encoding='utf-8', newline='') as handle:
        for r in csv.DictReader(handle):
            key = r['session'], int(r['division'])
            order = (*map(int, r['session'].split('-')), key[1], int(r['person_id']))
            if key not in divisions or (previous is not None and order <= previous):
                raise ValueError('Missing division, duplicate member or unsorted export')
            previous = order
            flags = [int(r[k]) for k in ('yea', 'nay', 'paired')]
            if any(f not in (0, 1) for f in flags):
                raise ValueError('Invalid exported flag')
            expected = ('Yea' if flags[0] else 'Nay') if not flags[2] and sum(flags[:2]) == 1 else ''
            if r['binary_vote'] != expected:
                raise ValueError('Export binary eligibility differs from flags')
            for i, flag in enumerate(flags):
                totals[key][i] += flag
            if expected:
                parties[key + (r['party_analytic'],)][expected == 'Nay'] += 1
            counts[r['session']] += 1
            seen.add(key)
    if seen != set(divisions):
        raise ValueError('Division without exported members')
    for key, r in divisions.items():
        if totals[key] != [int(r[k]) for k in ('yeas', 'nays', 'paired')]:
            raise ValueError(f'Export tally mismatch: {key}')
    for session, coverage in manifest['sessions'].items():
        if counts[session] != coverage['member_observations'] or sum(k[0] == session for k in divisions) != coverage['divisions']:
            raise ValueError(f'Export coverage mismatch: {session}')
    checked = set()
    with Path(classification).open(encoding='utf-8', newline='') as handle:
        for r in csv.DictReader(handle):
            key = r['session'], int(r['division']), r['party']
            if key in checked or key[:2] not in divisions:
                raise ValueError('Duplicate or unknown E1 division')
            yea, nay = parties[key]
            defined = yea != nay
            if (r['majority_defined'] != str(defined) or int(r['binary_members']) != yea + nay
                    or r['dissenters'] != (str(min(yea, nay)) if defined else '')):
                raise ValueError(f'Export/E1 denominator mismatch: {key}')
            checked.add(key)
    expected_keys = {(s, d, p) for s, d in divisions if s != '40-1'
                     for p in ('Conservative', 'Liberal', 'NDP', 'Bloc Québécois', 'Green Party')}
    if checked != expected_keys:
        raise ValueError('Incomplete E1 comparison universe')
    print(f'Export round-trip: {sum(counts.values())} members; {len(checked)} E1 party/division denominators match')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset', required=True, type=Path)
    parser.add_argument('--classification', required=True, type=Path)
    args = parser.parse_args()
    verify(args.dataset, args.classification)

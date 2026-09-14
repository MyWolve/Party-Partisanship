"""Fail-closed integrity gate for the corpus and documented source repairs.

python check_data.py [44-1 45-1] [--output audit/integrity.json]
No network calls, plotting imports, or blanket tally tolerances.
"""
import argparse
import csv
import json
import re
from datetime import datetime
from pathlib import Path

import bill_info
from vote_data import ROOT, decisions, read_vote_rows, tally

SESSIONS = ('38-1', '39-1', '39-2', '40-1', '40-2', '40-3', '41-1',
            '41-2', '42-1', '43-1', '43-2', '44-1', '45-1')


class IntegrityError(ValueError):
    pass


def check_session(session, directory, audit_records=None):
    problems, warnings = [], []
    try:
        metadata = bill_info.load_vote_metadata(directory)
    except (OSError, ValueError, csv.Error) as error:
        return [f'metadata: {error}'], []
    if not metadata:
        return ['Missing or empty metadata'], []
    files = {int(m.group(1)): p for p in Path(directory).iterdir()
             if (m := re.fullmatch(r'file_(\d+)\.csv', p.name))}
    for n in sorted(set(metadata) - set(files)):
        problems.append(f'{n}: missing member file')
    for n in sorted(set(files) - set(metadata)):
        problems.append(f'{n}: orphan member file')
    for n in sorted(set(metadata) & set(files)):
        try:
            m = metadata[n]
            datetime.fromisoformat(m['date'])
            expected = tuple(int(m[k]) for k in ('yeas', 'nays', 'paired'))
            if min(expected) < 0:
                raise ValueError('Negative tally')
            rows = read_vote_rows(files[n])
            if not rows:
                raise ValueError('Empty member file')
            if tally(rows) != expected:
                raise ValueError(f'Flag totals {tally(rows)} != metadata {expected}')
            if audit_records is not None:
                for r in rows:
                    if r['vote'] == 'Yea/Nay' or (r['vote'] and r['paired']):
                        audit_records.append(dict(session=session, division=n, **r))
            if m['category'] in ('other', 'unknown_bill'):
                warnings.append(f'{n}: unresolved business category ({m["category"]})')
        except (OSError, ValueError, KeyError, csv.Error) as error:
            problems.append(f'{n}: {error}')
    return problems, warnings


def require_valid_corpus(root=ROOT, sessions=None):
    root = Path(root)
    decisions.cache_clear()
    bill_info.load_designations.cache_clear()
    bill_info.load_designations()
    wanted = tuple(sessions) if sessions is not None else SESSIONS
    if not wanted or set(wanted) - set(SESSIONS):
        raise IntegrityError('Unknown or empty session selection')
    if sessions is None:
        actual_sessions = {p.name.replace('Parliament_', '') for p in root.glob('Parliament_*') if p.is_dir()}
        if actual_sessions != set(SESSIONS):
            raise IntegrityError(f'Session universe changed: {sorted(actual_sessions ^ set(SESSIONS))}')
    from tools.build_audit_data import build
    for name, content in build().items():
        if (ROOT / name).read_text(encoding='utf-8') != content:
            raise IntegrityError(f'Audit derivation changed: {name}')
    result = {'status': 'pass', 'sessions': {}, 'documented_repairs': decisions(), 'combination_votes_excluded': []}
    for session in wanted:
        directory = root / f'Parliament_{session}'
        if not directory.is_dir():
            problems, warnings = ['Missing session directory'], []
        else:
            problems, warnings = check_session(session, directory, result['combination_votes_excluded'])
        result['sessions'][session] = {'problems': problems, 'warnings': warnings}
    if any(s['problems'] for s in result['sessions'].values()):
        result['status'] = 'fail'
        error = IntegrityError('Corpus integrity failed: ' + '; '.join(
            f'{s}: {p}' for s, v in result['sessions'].items() for p in v['problems']))
        error.report = result
        raise error
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('sessions', nargs='*')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    try:
        report = require_valid_corpus(sessions=args.sessions or None)
    except (OSError, ValueError, csv.Error, AssertionError) as error:
        report = getattr(error, 'report', {'status': 'fail', 'error': str(error)})
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(f'Integrity: {report["status"].upper()}')
    for session, value in report.get('sessions', {}).items():
        print(f'{session}: {len(value["problems"])} problems, {len(value["warnings"])} classification warnings')
        for message in value['problems'] + value['warnings']:
            print('  ' + message)
    if 'error' in report:
        print(report['error'])
    print(f'{len(report.get("documented_repairs", {}))} documented source repairs; no blanket tolerance')
    return 0 if report['status'] == 'pass' else 1


if __name__ == '__main__':
    raise SystemExit(main())

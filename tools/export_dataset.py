"""Export the effective frozen corpus to a new directory; never collect live data."""
import argparse
import csv
import gzip
import io
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import bill_info
from check_data import SESSIONS, require_valid_corpus
from experiment_io import write_csv, write_json
from provenance import digest, verify_inputs
from vote_data import binary_vote, decisions, read_vote_rows, tally
from visualize_parliament import AFFILIATION_ALIASES, PARTIES
from tools.recover_sponsors import build as build_sponsors

MEMBER_FIELDS = ['session', 'division', 'person_id', 'member', 'party_raw', 'party_analytic',
                 'yea', 'nay', 'paired', 'binary_vote', 'repair_id', 'source_file']


def member_record(session, division, row, decision):
    changed = ('replacement' in decision or row['member_id'] in decision.get('dual_member_ids', [])
               or row['member_id'] in {r['member_id'] for r in decision.get('append_rows', [])})
    party = AFFILIATION_ALIASES.get(row['party'], row['party'])
    return dict(session=session, division=division, person_id=row['member_id'], member=row['member'],
        party_raw=row['party'], party_analytic=party if party in PARTIES else 'Independent',
        yea=int(row['vote'] in ('Yea', 'Yea/Nay')), nay=int(row['vote'] in ('Nay', 'Yea/Nay')),
        paired=int(row['paired']), binary_vote=binary_vote(row),
        repair_id=f'{session}/{division}' if changed else '',
        source_file=f'Parliament_{session}/file_{division}.csv')


def export(destination):
    corpus = verify_inputs()
    require_valid_corpus()
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=False)
    metadata, counts = [], {}
    # Empty filename and fixed mtime remove host paths/timestamps from gzip.
    with (destination/'members.csv.gz').open('wb') as raw:
        with gzip.GzipFile(filename='', mode='wb', fileobj=raw, mtime=0, compresslevel=6) as compressed:
            with io.TextIOWrapper(compressed, encoding='utf-8', newline='') as handle:
                writer = csv.DictWriter(handle, fieldnames=MEMBER_FIELDS, lineterminator='\n')
                writer.writeheader()
                for session in SESSIONS:
                    directory = ROOT/f'Parliament_{session}'
                    meta = bill_info.load_vote_metadata(directory)
                    count = 0
                    for number, m in sorted(meta.items()):
                        rows = read_vote_rows(directory/f'file_{number}.csv')
                        decision = decisions().get(f'{session}/{number}', {})
                        exported = [member_record(session, number, r, decision) for r in rows]
                        ids = [r['person_id'] for r in exported]
                        if any(not i.isdigit() or int(i) <= 0 for i in ids) or len(ids) != len(set(ids)):
                            raise ValueError(f'{session}/{number}: invalid exported person identifiers')
                        expected = tuple(int(m[k]) for k in ('yeas', 'nays', 'paired'))
                        actual = tuple(sum(r[k] for r in exported) for k in ('yea', 'nay', 'paired'))
                        if actual != expected or tally(rows) != expected:
                            raise ValueError(f'{session}/{number}: export tally mismatch')
                        writer.writerows(sorted(exported, key=lambda r: int(r['person_id'])))
                        count += len(exported)
                        metadata.append(dict(session=session, division=number, date=m['date'], subject=m['subject'],
                            result=m['result'], yeas=int(m['yeas']), nays=int(m['nays']), paired=int(m['paired']),
                            bill=m['bill_number'], bill_type=m['bill_type'], bill_type_source=m['bill_type_source'],
                            category=m['category'], stage=m['stage'] or '', confidence_proxy=int(m['confidence']),
                            repair_id=f'{session}/{number}' if decision else '',
                            source_file=f'Parliament_{session}/votes_metadata.csv'))
                    counts[session] = dict(divisions=len(meta), member_observations=count,
                                           first_date=min(m['date'] for m in meta.values()),
                                           last_date=max(m['date'] for m in meta.values()))
    write_csv(destination/'divisions.csv', metadata)
    write_csv(destination/'bill_sponsors.csv', build_sponsors())
    write_json(destination/'repairs.json', decisions())
    for name in ('sources.json',):
        write_json(destination/name, json.loads((ROOT/'evidence'/name).read_text(encoding='utf-8')))
    if verify_inputs() != corpus:
        raise ValueError('Inputs changed during export')
    files = {p.name: digest(p) for p in sorted(destination.iterdir())}
    # CSV content is portable; gzip bytes can differ with the zlib version.
    with gzip.open(destination/'members.csv.gz', 'rb') as handle:
        import hashlib
        member_content = hashlib.file_digest(handle, 'sha256').hexdigest()
    write_json(destination/'manifest.json', dict(schema_version=2, corpus_sha256=corpus,
        snapshot_id=f'corpus-{corpus[:12]}', sessions=counts,
        members_csv_sha256=member_content,
        files=files, hash_convention='SHA256 of UTF-8 LF content; decompress gzip before hashing',
        documentation='data/README.md',
        note='Observed member records only; absence is not a recorded abstention. 45-1 is incomplete.'))
    print(f'Export: {len(metadata)} divisions, {sum(c["member_observations"] for c in counts.values())} member observations')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', required=True, type=Path)
    export(parser.parse_args().output_dir)

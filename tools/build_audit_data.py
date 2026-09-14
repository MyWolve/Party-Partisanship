"""Rebuild reviewed corrections from frozen official sources, without network.

--check compares the products instead of writing them. Deliberate assertions
bind each repair to the reviewed record and reject ambiguous member matching.
"""
import argparse
import gzip
import csv
import hashlib
import html
import io
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from vote_data import parse_vote_text, text_hash, tally


def xml_rows(name):
    return [{c.tag: c.text or '' for c in e}
            for e in ET.fromstring(gzip.decompress((ROOT / 'evidence' / (name+'.gz')).read_bytes()))]


def journal_names(number):
    s = gzip.decompress((ROOT / 'evidence' / f'42-1-{number}-journals.html.gz').read_bytes()).decode('utf-8')
    start = s.index(f'Division No. {number}')
    block = s[start:s.index('</table>', start)]
    groups = block.split('class="DivisionType">')[2::2]
    return {vote: [html.unescape(x) for x in re.findall(
        r'<span class="DivisionItem">(.*?)<br>', part, re.S)]
        for vote, part in zip(('Yea', 'Nay'), groups)}


def normalize(s):
    return re.sub(r'[^\w]', '', s).lower()


def match_name(name, roster):
    match = re.fullmatch(r'(.*?) \((.*)\)', name)
    last, seat = match.groups() if match else (name, None)
    hits = [p for p in roster if normalize(p['PersonOfficialLastName']) == normalize(last)
            and (not seat or normalize(p['ConstituencyName']) == normalize(seat))]
    if len(hits) != 1:
        raise ValueError(f'Ambiguous/unmatched Journal name: {name}')
    return hits[0]


def member(p, vote):
    return {'member_id': p['PersonId'],
            'member': f"{p['PersonOfficialFirstName']} {p['PersonOfficialLastName']} ({p['ConstituencyName']})",
            'party': p['CaucusShortName'], 'vote': vote, 'paired': False}


def csv_text(rows):
    out = io.StringIO(newline='')
    w = csv.writer(out, lineterminator='\n')
    w.writerow(['Person ID', 'Member of Parliament', 'Political Affiliation', 'Member Voted', 'Paired'])
    for r in rows:
        w.writerow([r['member_id'], r['member'], r['party'], r['vote'], 'Paired' if r['paired'] else ''])
    return out.getvalue()


def build():
    if not __debug__:
        raise ValueError('Audit derivation must run without Python optimization (-O)')
    sources = json.loads((ROOT / 'evidence/sources.json').read_text(encoding='utf-8'))
    for name, source in sources.items():
        if hashlib.sha256((ROOT / 'evidence' / name).read_bytes()).hexdigest() != source['sha256']:
            raise ValueError(f'Evidence checksum mismatch: {name}')
    issues = json.loads((ROOT / 'audit/baseline_discrepancies.json').read_text(encoding='utf-8'))
    result, files = {}, {}
    for issue in sorted(issues, key=lambda r: (r['session'], r['division'])):
        session, number = issue['session'], issue['division']
        directory = ROOT / f'Parliament_{session}'
        raw = (directory / f'file_{number}.csv').read_text(encoding='utf-8')
        rows = parse_vote_text(raw)
        with (directory / 'votes_metadata.csv').open(encoding='utf-8-sig') as stream:
            meta = next(r for r in csv.DictReader(stream) if int(r['vote_number']) == number)
        decision = {'raw_sha256': text_hash(raw), 'raw_metadata': meta,
                    'source_files': [f'evidence/{session}-{number}.xml']}
        official = xml_rows(f'{session}-{number}.xml')
        if number == 871 and session == '42-1':
            assert not rows and not official
            names = journal_names(871)
            roster = xml_rows('42-1-872.xml')
            assert all(p['DecisionEventDateTime'][:10] == meta['date'][:10] for p in roster)
            repaired = [member(match_name(name, roster), vote) for vote in ('Yea', 'Nay') for name in names[vote]]
            assert tally(repaired) == (172, 134, 0)
            assert len({r['member_id'] for r in repaired}) == 306
            path = 'audit/derived/42-1-871.csv'
            files[path] = csv_text(repaired)
            decision.update(replacement=path, replacement_sha256=text_hash(files[path]),
                metadata_override={'yeas': '172', 'nays': '134', 'paired': '0', 'result': 'Agreed To'},
                reason='Journal roll call; identities and affiliations uniquely joined to the same-sitting division 872 roster. No votes copied from 872.',
                treatment='restore_division')
            decision['source_files'] += ['evidence/42-1-871-journals.html', 'evidence/42-1-872.xml']
        elif number == 724 and session == '42-1':
            # Match every Journal name against the original XML plus the missing member.
            before = next(p for p in xml_rows('42-1-723.xml') if p['PersonId'] == '88595')
            after = next(p for p in xml_rows('42-1-725.xml') if p['PersonId'] == '88595')
            assert before['CaucusShortName'] == 'Groupe parlementaire québécois'
            assert after['CaucusShortName'] == 'Québec debout'
            assert before['PersonOfficialLastName'] == after['PersonOfficialLastName'] == 'Pauzé'
            assert before['DecisionEventDateTime'][:10] < meta['date'][:10] < after['DecisionEventDateTime'][:10]
            assert '88595' not in {r['member_id'] for r in rows}
            original = {r['member_id']: r for r in rows}
            names = journal_names(724)
            joined = [(match_name(name, official + [after])['PersonId'], vote)
                      for vote in ('Yea', 'Nay') for name in names[vote]]
            assert len(joined) == len(set(p for p, _ in joined)) == 285
            assert all(original[p]['vote'] == v for p, v in joined if p in original)
            assert [(p, v) for p, v in joined if p not in original] == [('88595', 'Yea')]
            added = member(after, 'Yea')
            # Both bracketing group names map to the project's Independent aggregate.
            # Do not claim an exact original caucus label for the missing record.
            added['party'] = 'Independent'
            decision.update(append_rows=[added], treatment='restore_member',
                reason='Journal includes Monique Pauzé (Yea). Adjacent-day XML rosters use two minor-group labels, both aggregated as Independent; exact June 5 group label remains unresolved.')
            decision['source_files'] += ['evidence/42-1-724-journals.html', 'evidence/42-1-723.xml', 'evidence/42-1-725.xml']
            assert tally(rows + [added]) == (40, 245, 0)
        else:
            by_id = {p['PersonId']: p for p in official}
            assert set(by_id) == {r['member_id'] for r in rows}
            dual = sorted(p['PersonId'] for p in official if p['IsVoteYea'] == p['IsVoteNay'] == 'true')
            assert dual
            for r in rows:
                p = by_id[r['member_id']]
                assert r['party'] == p['CaucusShortName']
                if r['member_id'] in dual:
                    assert r['vote'] in ('Yea', 'Nay')
                    r['vote'] = 'Yea/Nay'
                else:
                    assert (r['vote'] == 'Yea') == (p['IsVoteYea'] == 'true')
                    assert (r['vote'] == 'Nay') == (p['IsVoteNay'] == 'true')
                assert r['paired'] == (p['IsVotePaired'] == 'true')
            assert tally(rows) == tuple(int(meta[k]) for k in ('yeas', 'nays', 'paired'))
            decision.update(dual_member_ids=dual, treatment='exclude_dual_from_binary_metrics',
                reason='Official XML has both Yea and Nay flags. Retain both for tally verification; exclude this member-division from binary metrics.')
        decision['source_files'] = [p+'.gz' for p in decision['source_files']]
        result[f'{session}/{number}'] = decision
    files['audit/data_decisions.json'] = json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True) + '\n'
    return files


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    for name, text in build().items():
        path = ROOT / name
        if args.check:
            if not path.exists() or path.read_text(encoding='utf-8') != text:
                raise ValueError(f'Rebuilt audit data differs: {name}')
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding='utf-8', newline='\n')
        print(('Verified ' if args.check else 'Wrote ') + name)


if __name__ == '__main__':
    main()

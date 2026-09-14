"""Independently re-tally exported member CSVs; no project-loader imports."""
import csv
import gzip
import sys
from collections import defaultdict
from pathlib import Path


def verify(directory):
    directory = Path(directory)
    def read(name):
        with (directory/name).open(encoding='utf-8') as stream:
            return list(csv.DictReader(stream))
    divisions = read('divisions.csv')
    known = {(r['session'],r['division']) for r in divisions}
    assert len(known) == len(divisions), 'Duplicate divisions'
    tally, parties = defaultdict(lambda:[0,0,0]), defaultdict(lambda:[0,0])
    seen, count = set(), 0
    with gzip.open(directory/'members.csv.gz','rt',encoding='utf-8') as stream:
        for r in csv.DictReader(stream):
            key = r['session'],r['division']
            assert key in known, 'Orphan member'
            identity = (*key,r['member_id'])
            assert r['member_id'] and identity not in seen, 'Missing/duplicate member ID'
            seen.add(identity)
            assert r['vote'] in ('Yea','Nay','Yea/Nay','') and r['paired'] in ('True','False')
            tally[key][0] += r['vote'] in ('Yea','Yea/Nay')
            tally[key][1] += r['vote'] in ('Nay','Yea/Nay')
            tally[key][2] += r['paired']=='True'
            binary = r['vote'] if r['paired']=='False' and r['vote'] in ('Yea','Nay') else ''
            assert r['binary_vote']==binary
            if binary:
                parties[(*key,r['party'])][binary=='Nay'] += 1
            count += 1
    for r in divisions:
        assert tally[r['session'],r['division']]==[int(r[c]) for c in ['yeas','nays','paired']], 'Tally mismatch'
    party_rows=read('party_votes.csv')
    party_keys={(r['session'],r['division'],r['party']) for r in party_rows}
    assert len(party_keys)==len(party_rows)==5*len(divisions), 'Party table coverage mismatch'
    for r in party_rows:
        assert parties[r['session'],r['division'],r['party']]==[int(r['yea']),int(r['nay'])], 'Binary denominator mismatch'
    print(f'Export verified: {len(divisions)} divisions, {count} members, {len(party_rows)} party tallies')


if __name__=='__main__':
    verify(sys.argv[1])

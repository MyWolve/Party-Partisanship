"""Reconcile deposited member/division records against the frozen corpus.

Matching uses names and constituencies, never voting choices. Every observable
record must have a unique identity match; ambiguous joins fail closed.
"""
import argparse
import collections
import csv
from datetime import datetime
from pathlib import Path
import re
import sys
import tempfile
import unicodedata
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from vote_data import read_vote_rows, binary_vote
from experiment_io import write_csv, write_json
from provenance import verify_inputs

PARTIES = {'Liberal Party of Canada': 'Liberal', 'Conservative Party of Canada': 'Conservative',
           'New Democratic Party': 'NDP', 'Bloc Quebecois': 'Bloc Québécois',
           'Green Party of Canada': 'Green Party'}
FLAGS = {'1': ('Yea', False), '2': ('Nay', False), '3': ('', True),
         '4': ('Yea/Nay', False), '5': ('Yea', True), '6': ('Nay', True), '7': ('Yea/Nay', True)}
ABSENT = {'9', '99'}
FIELDS = ['parliament','session','division','person_id','member','deposit_term_id',
          'issue','official_vote','official_paired','deposit_code','official_party','deposit_party']


def normalize(value):
    text = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode().lower()
    return re.sub('[^a-z0-9]', '', text)


def match_member(name, riding, indexes):
    last, first = name.split(',', 1)
    candidates = [(normalize(first+last), 'full_name'),
                  ((normalize(last), normalize(riding)), 'surname_constituency'),
                  ((normalize(first.split()[0]), normalize(last)), 'first_surname')]
    ambiguous = None
    for key, method in candidates:
        hits = indexes[method].get(key, set())
        if ambiguous is not None and hits:
            hits = hits & ambiguous
        if len(hits) == 1:
            return next(iter(hits)), method
        if len(hits) > 1:
            ambiguous = hits
    if ambiguous:
        raise ValueError(f'Ambiguous identity: {name}, {riding}')
    return None, 'no_official_observation'


def reconcile(root=ROOT):
    root = Path(root)
    crosswalk, differences, summaries, division_dates = [], [], [], []
    for parliament in (38,39,40):
        indexes = {k: collections.defaultdict(set) for k in ('full_name','surname_constituency','first_surname')}
        official, labels, dates = {}, {}, {}
        for directory in sorted(root.glob(f'Parliament_{parliament}-*')):
            session = directory.name.replace('Parliament_', '')
            with (directory/'votes_metadata.csv').open(encoding='utf-8-sig') as stream:
                for row in csv.DictReader(stream): dates[(session,int(row['vote_number']))] = row['date'][:10]
            for path in sorted(directory.glob('file_*.csv'), key=lambda p: int(p.stem.split('_')[1])):
                number = int(path.stem.split('_')[1])
                rows = read_vote_rows(path)
                official[(session,number)] = {r['member_id']: r for r in rows}
                for r in rows:
                    person = r['member_id']
                    if not person: raise ValueError('Reconciliation requires Person IDs')
                    labels[person] = r['member']
                    name, riding = r['member'].rsplit(' (',1)
                    last = name.split()[-1]
                    indexes['full_name'][normalize(name)].add(person)
                    indexes['surname_constituency'][(normalize(last),normalize(riding))].add(person)
                    indexes['first_surname'][(normalize(name.split()[0]),normalize(last))].add(person)
        with (root/f'experiments/experiment_7_data/House-{parliament}.tab').open(encoding='utf-8') as stream:
            reader = csv.DictReader(stream, delimiter='\t')
            headers = reader.fieldnames or []
            if len(headers)!=len(set(headers)): raise ValueError('Duplicate deposit columns')
            rows = list(reader)
        date_rows = [r for r in rows if r['vote.id']=='Date']
        if len(date_rows)!=1: raise ValueError('Expected exactly one deposit date row')
        cols = [c for c in headers if re.fullmatch(r'H\d+S\d+V\d+',c)]
        keys = {}
        for col in cols:
            p,s,v = map(int,re.fullmatch(r'H(\d+)S(\d+)V(\d+)',col).groups())
            if p!=parliament: raise ValueError('Wrong parliament in deposit division')
            keys[col]=(f'{p}-{s}',v)
            if keys[col] not in official: raise ValueError(f'Missing official division {col}')
            day=datetime.strptime(date_rows[0][col],'%Y.%m.%d').date().isoformat()
            division_dates.append({'division_id':col,'official_date':dates[keys[col]],'deposit_date':day,'date_matches':day==dates[keys[col]]})
        if set(keys.values())!=set(official): raise ValueError('Division universes differ')
        members=[]; term_ids=set()
        for r in rows:
            if r['vote.id']=='Date': continue
            term=r['Id.2']
            if not term or term in term_ids: raise ValueError('Missing/duplicate deposit term ID')
            term_ids.add(term)
            for col in cols:
                if r[col] not in set(FLAGS)|ABSENT: raise ValueError(f'Unsupported deposit code {r[col]}')
            person,method=match_member(r['Name'],r['Riding'],indexes)
            observable=sum(r[c] in FLAGS for c in cols)
            if person is None and observable: raise ValueError(f'Unmatched observable member: {r["Name"]}')
            crosswalk.append({'parliament':parliament,'deposit_term_id':term,'deposit_name':r['Name'],
                'deposit_constituency':r['Riding'],'person_id':person or '', 'method':method,
                'observable_records':observable})
            members.append((person,r))
        counts=collections.Counter()
        for col,key in keys.items():
            deposited={}
            for person,r in members:
                if r[col] not in FLAGS: continue
                if person in deposited: raise ValueError(f'Overlapping observable affiliation terms: {col}/{person}')
                deposited[person]=r
            current=official[key]
            for person in sorted(set(current)|set(deposited)):
                a,b=current.get(person),deposited.get(person)
                counts['union_observable_records']+=1
                issues=[]
                if a is None: issues.append('deposit_only_observation')
                elif b is None: issues.append('official_only_observation')
                else:
                    counts['joined_records']+=1
                    vote,paired=FLAGS[b[col]]
                    if (a['vote'],a['paired'])!=(vote,paired): issues.append('vote_flags')
                    raw_party=b['Party.Name'].strip()
                    party=PARTIES.get(raw_party,'Independent')
                    official_party=a['party'] if a['party'] in set(PARTIES.values()) else 'Independent'
                    if official_party!=party: issues.append('analytic_party')
                    if binary_vote(a)!=binary_vote({'vote':vote,'paired':paired}): counts['binary_vote_differences']+=1
                if not issues: counts['exact_flag_and_analytic_party_matches']+=1
                for issue in issues:
                    counts[issue]+=1
                    differences.append(dict(parliament=parliament,session=key[0],division=key[1],person_id=person,
                        member=labels.get(person,''),deposit_term_id=b['Id.2'] if b else '',issue=issue,
                        official_vote=a['vote'] if a else '',official_paired=a['paired'] if a else '',
                        deposit_code=b[col] if b else '',official_party=a['party'] if a else '',
                        deposit_party=b['Party.Name'] if b else ''))
        summaries.append({'parliament':parliament,'divisions':len(cols), 'deposit_terms':len(members),
                          'unmatched_nonobserved_terms':sum(person is None for person,_ in members),**dict(counts)})
    return crosswalk, differences, summaries, division_dates


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir',type=Path,default=ROOT/'audit/reconciliation')
    parser.add_argument('--check',action='store_true',help='Compare with saved reconciliation without replacing it')
    args=parser.parse_args()
    corpus=verify_inputs()
    crosswalk,differences,summary,dates=reconcile()
    with tempfile.TemporaryDirectory() as directory:
        output=Path(directory)
        write_csv(output/'division_dates.csv',dates)
        write_csv(output/'member_crosswalk.csv',crosswalk)
        write_csv(output/'differences.csv',differences,FIELDS)
        write_json(output/'summary.json',{'corpus_sha256':corpus,'parliaments':summary})
        if args.check:
            for p in output.iterdir():
                if p.read_text(encoding='utf-8')!=(args.output_dir/p.name).read_text(encoding='utf-8'):
                    raise ValueError(f'Reconciliation changed: {p.name}; review required')
        else:
            args.output_dir.mkdir(parents=True,exist_ok=True)
            for p in output.iterdir(): (args.output_dir/p.name).write_bytes(p.read_bytes())
    print(summary)

if __name__=='__main__': main()

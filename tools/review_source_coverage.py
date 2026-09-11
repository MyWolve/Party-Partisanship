"""Frozen coverage review of later-session XML and session-wide bill exports.

--fetch is the only network mode. Ordinary checks use archived source bytes.
The fixed 35-division sample is coverage-oriented, not a statistical sample.
"""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import time
import xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from bill_data import parse_bill_xml
from check_data import SESSIONS
from experiment_io import write_csv, write_json
from vote_data import read_vote_rows
from provenance import verify_inputs
from can_scrape import fetch
from bill_info import classify_vote


def source_urls(root=ROOT):
    selection=json.loads((root/'audit/source_review_selection.json').read_text(encoding='utf-8'))
    urls={f'legisinfo-{s}-current.xml':f'https://www.parl.ca/legisinfo/en/bills/xml?parlsession={s}' for s in SESSIONS}
    urls.update({f'review-{r["session"]}-{r["division"]}.xml':
        f'https://www.ourcommons.ca/members/en/votes/{r["session"].replace("-","/")}/{r["division"]}/xml' for r in selection['votes']})
    return urls


def fetch_sources(root=ROOT):
    path=root/'evidence/sources.json';ledger=json.loads(path.read_text(encoding='utf-8'))
    for name,url in source_urls(root).items():
        target=root/'evidence'/name
        if target.exists():
            if name not in ledger or ledger[name]['url']!=url or hashlib.sha256(target.read_bytes()).hexdigest()!=ledger[name]['sha256']:
                raise ValueError(f'Existing source differs: {name}')
            continue
        response=fetch(url);ET.fromstring(response.content)
        if name.startswith('legisinfo-'):
            session=name.removeprefix('legisinfo-').removesuffix('-current.xml')
            parse_bill_xml(response.content,session)
        target.write_bytes(response.content)
        ledger[name]={'url':url,'retrieved_date':datetime.now(timezone.utc).date().isoformat(),
                      'sha256':hashlib.sha256(response.content).hexdigest()}
        write_json(path,ledger)
        print(f'Archived {name}: {len(response.content)} bytes',flush=True)


def parse_vote_xml(data, session, division):
    result={}; metadata=set()
    root=ET.fromstring(data)
    if root.tag!='ArrayOfVoteParticipant':raise ValueError('Unexpected vote XML root')
    for element in root:
        if element.tag!='VoteParticipant':raise ValueError('Unexpected vote XML record')
        keys=[c.tag for c in element]
        if len(keys)!=len(set(keys)):raise ValueError('Duplicate vote XML fields')
        row={c.tag:(c.text or '').strip() for c in element}
        required={'ParliamentNumber','SessionNumber','DecisionDivisionNumber','PersonId','CaucusShortName',
                  'IsVoteYea','IsVoteNay','IsVotePaired','DecisionEventDateTime','DecisionResultName'}
        if not required.issubset(row) or not row['CaucusShortName'] or not row['DecisionResultName']:
            raise ValueError('Incomplete vote XML record')
        datetime.fromisoformat(row['DecisionEventDateTime'])
        if f"{row['ParliamentNumber']}-{row['SessionNumber']}"!=session or int(row['DecisionDivisionNumber'])!=division:
            raise ValueError('Wrong vote/session in XML')
        person=row['PersonId']
        if not person.isdigit() or person in result:raise ValueError('Invalid/duplicate XML Person ID')
        flags=[row[k] for k in ('IsVoteYea','IsVoteNay','IsVotePaired')]
        if any(flag not in ('true','false') for flag in flags):raise ValueError('Invalid XML flag')
        yea,nay,paired=[f=='true' for f in flags]
        if not any((yea,nay,paired)):raise ValueError('Unobservable XML row')
        vote='Yea/Nay' if yea and nay else 'Yea' if yea else 'Nay' if nay else ''
        result[person]={'vote':vote,'paired':paired,'party':row['CaucusShortName']}
        metadata.add((row['DecisionEventDateTime'],row['DecisionResultName']))
    if not result or len(metadata)!=1:raise ValueError('Empty/inconsistent vote XML')
    return result,next(iter(metadata))


def build(root=ROOT):
    coverage=[]; changes=[]; votes=[]; differences=[]; classification=[]
    for session in SESSIONS:
        baseline=root/'House of Commons'/f'{session}.xml'
        old=parse_bill_xml(baseline.read_bytes(),session) if baseline.exists() else {}
        new=parse_bill_xml((root/'evidence'/f'legisinfo-{session}-current.xml').read_bytes(),session)
        common=set(old)&set(new)
        coverage.append({'session':session,'baseline_present':baseline.exists(),'frozen_bills':len(old),'current_bills':len(new),
            'added':len(set(new)-set(old)),'removed':len(set(old)-set(new)),
            'type_changes':sum(old[n]['type']!=new[n]['type'] for n in common),
            'title_changes':sum(old[n]['title']!=new[n]['title'] for n in common),
            'sponsor_changes':sum(old[n]['sponsor']!=new[n]['sponsor'] for n in common),
            'lost_sponsors':sum(bool(old[n]['sponsor']) and not new[n]['sponsor'] for n in common)})
        for number in sorted(set(old)|set(new)):
            for field in ('type','title','sponsor'):
                before=old.get(number,{}).get(field);after=new.get(number,{}).get(field)
                if before!=after:changes.append({'session':session,'bill':number,'field':field,'before':before,'after':after})
        if not baseline.exists():
            with (root/f'Parliament_{session}'/'votes_metadata.csv').open(encoding='utf-8-sig') as stream:
                for row in csv.DictReader(stream):
                    before=classify_vote(row['subject'],row['bill_number'],{})
                    after=classify_vote(row['subject'],row['bill_number'],new)
                    classification.append({'session':session,'division':row['vote_number'],
                        'bill':after['bill_number'],'before_category':before['category'],
                        'after_category':after['category'],'before_source':before['bill_type_source'],
                        'after_source':after['bill_type_source']})
    selection=json.loads((root/'audit/source_review_selection.json').read_text(encoding='utf-8'))
    expected=[]
    for session in SESSIONS:
        if int(session.split('-')[0])<41:continue
        nums=sorted(int(p.stem.split('_')[1]) for p in (root/f'Parliament_{session}').glob('file_*.csv'))
        expected.extend({'session':session,'division':n} for n in sorted({nums[(len(nums)-1)*i//4] for i in range(5)}))
    if selection['votes']!=expected:raise ValueError('Coverage selection differs from the declared deterministic rule')
    for selected in selection['votes']:
        session,division=selected['session'],selected['division']
        fresh,meta=parse_vote_xml((root/'evidence'/f'review-{session}-{division}.xml').read_bytes(),session,division)
        directory=root/f'Parliament_{session}'
        old={r['member_id']:r for r in read_vote_rows(directory/f'file_{division}.csv')}
        with (directory/'votes_metadata.csv').open(encoding='utf-8-sig') as stream:
            metadata=next(r for r in csv.DictReader(stream) if int(r['vote_number'])==division)
        record={'session':session,'division':division,'frozen_observations':len(old),'fresh_observations':len(fresh),
                'matching_observations':0,'differences':0,'date_matches':meta[0]==metadata['date'],
                'result_matches':meta[1]==metadata['result']}
        for person in sorted(set(old)|set(fresh)):
            a={k:old[person][k] for k in ('vote','paired','party')} if person in old else None
            b=fresh.get(person)
            if a==b:record['matching_observations']+=1
            else:
                record['differences']+=1
                differences.append({'session':session,'division':division,'person_id':person,
                    'frozen':json.dumps(a,sort_keys=True,ensure_ascii=False),'fresh':json.dumps(b,sort_keys=True,ensure_ascii=False)})
        votes.append(record)
    return coverage,changes,votes,differences,classification


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fetch',action='store_true')
    parser.add_argument('--check',action='store_true')
    args=parser.parse_args()
    if args.fetch:fetch_sources();return
    verify_inputs()
    coverage,changes,votes,differences,classification=build()
    with tempfile.TemporaryDirectory() as name:
        temp=Path(name)
        write_csv(temp/'bill_coverage.csv',coverage)
        write_csv(temp/'bill_changes.csv',changes,['session','bill','field','before','after'])
        write_csv(temp/'vote_sample.csv',votes)
        write_csv(temp/'vote_differences.csv',differences,['session','division','person_id','frozen','fresh'])
        write_csv(temp/'classification_upgrade.csv',classification)
        destination=ROOT/'audit/source_coverage'
        if args.check:
            for p in temp.iterdir():
                if p.read_text(encoding='utf-8')!=(destination/p.name).read_text(encoding='utf-8'):
                    raise ValueError(f'Source coverage changed: {p.name}')
        else:
            destination.mkdir(parents=True,exist_ok=True)
            for p in temp.iterdir():(destination/p.name).write_bytes(p.read_bytes())
    print(f"Reviewed {len(coverage)} bill sessions and {len(votes)} sampled divisions; {len(differences)} member differences")

if __name__=='__main__':main()

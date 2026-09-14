"""Collect and compare LEGISinfo in a new review directory; never promote it."""
import argparse
import hashlib
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from bill_data import parse_bill_xml, parse_bill_detail
from can_scrape import fetch
from experiment_io import write_json


def compare_bills(old,new):
    changes=[]
    for number in sorted(set(old)|set(new)):
        if old.get(number)!=new.get(number):
            changes.append({'bill':number,'kind':'added' if number not in old else 'removed' if number not in new else 'changed',
                            'before':old.get(number),'after':new.get(number)})
    return changes


def collect(session, output, source_xml=None, root=ROOT, with_sponsors=False):
    if with_sponsors and source_xml is not None:
        raise ValueError('Sponsor retrieval is a live operation; omit --source-xml')
    if not re.fullmatch(r'[1-9]\d*-[1-9]\d*',session): raise ValueError('Invalid session')
    output=Path(output).resolve();output.mkdir(parents=True,exist_ok=False)
    url=f'https://www.parl.ca/legisinfo/en/bills/xml?parlsession={session}'
    report={'session':session,'status':'collecting','requested_url':url if source_xml is None else None,
            'started_utc':datetime.now(timezone.utc).isoformat(),'source':'live' if source_xml is None else 'local_file'}
    try:
        if source_xml is None:
            response=fetch(url);data=response.content
            report.update(resolved_url=response.url,http_status=response.status_code,content_type=response.headers.get('Content-Type',''))
        else: data=Path(source_xml).read_bytes()
        (output/'bills.xml').write_bytes(data)
        report.update(sha256=hashlib.sha256(data).hexdigest(),bytes=len(data))
        bills=parse_bill_xml(data,session)
        if with_sponsors:
            details=output/'details';details.mkdir()
            sponsors={}
            report['sponsor_responses']=[]
            for number in sorted(bills):
                detail_url=f'https://www.parl.ca/legisinfo/en/bill/{session}/{number.lower()}/json'
                response=fetch(detail_url)
                raw=response.content
                (details/f'{number}.json').write_bytes(raw)
                report['sponsor_responses'].append(dict(bill=number,url=detail_url,
                    resolved_url=response.url,http_status=response.status_code,
                    received_utc=datetime.now(timezone.utc).isoformat(),
                    content_type=response.headers.get('Content-Type',''),
                    bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
                detail=parse_bill_detail(raw,session,number)
                if any(detail[k]!=bills[number][k] for k in ('type','title')):
                    raise ValueError(f'Sponsor detail title/type differs: {number}')
                sponsors[number]=detail
                bills[number]['sponsor']=detail['sponsor']
            write_json(output/'bill_sponsors.json',sponsors)
            report['sponsor_identity_records']=len(sponsors)
        baseline=Path(root)/'House of Commons'/f'{session}.xml'
        old=parse_bill_xml(baseline.read_bytes(),session) if baseline.exists() else {}
        changes=compare_bills(old,bills)
        lost_sponsors=[number for number in sorted(set(old)&set(bills))
                       if old[number]['sponsor'] and not bills[number]['sponsor']]
        write_json(output/'normalized_bills.json',bills)
        write_json(output/'changes.json',changes)
        report.update(status='validated_review_snapshot',bills=len(bills),changed_bills=len(changes),
                      lost_sponsor_fields=lost_sponsors,
                      baseline_sha256=hashlib.sha256(baseline.read_bytes()).hexdigest() if baseline.exists() else None)
    except Exception as error:
        report.update(status='failed',error=f'{type(error).__name__}: {error}')
        raise
    finally:
        report['finished_utc']=datetime.now(timezone.utc).isoformat()
        write_json(output/'collection_manifest.json',report)
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session',required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--source-xml',type=Path,help='Validate an existing download offline')
    parser.add_argument('--with-sponsors',action='store_true',
                        help='Also archive per-bill JSON and recover sponsor Person IDs (extra live requests)')
    args=parser.parse_args()
    report=collect(args.session,args.output,args.source_xml,with_sponsors=args.with_sponsors)
    print(f"{report['status']}: {report['bills']} bills, {report['changed_bills']} changed; no corpus files replaced")

if __name__=='__main__': main()

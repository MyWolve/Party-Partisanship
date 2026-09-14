"""Select recorded votes, export reusable CSVs, and compare party dissent."""
import argparse
import csv
import gzip
import hashlib
import json
from collections import defaultdict
from pathlib import Path

import bill_info
from check_data import SESSIONS, require_valid_corpus
from vote_data import ROOT, read_vote_rows, binary_vote, decisions
from visualize_parliament import PARTIES, AFFILIATION_ALIASES, PARTY_COLORS

TRACKED = [p for p in PARTIES if p != 'Independent']


def analytic_party(raw):
    party = AFFILIATION_ALIASES.get(raw, raw)
    return party if party in PARTIES else 'Independent'


def party_counts(rows):
    """Independents remain in the export, but are not treated as one caucus."""
    counts = {p: [0, 0] for p in TRACKED}
    for row in rows:
        p, vote = analytic_party(row['party']), binary_vote(row)
        if p in counts and vote in ('Yea', 'Nay'):
            counts[p][vote == 'Nay'] += 1
    return counts


def summarize(observations, group_by):
    groups = defaultdict(list)
    for row in observations:
        # Unnumbered business cannot be interpreted as a bill.
        if group_by == 'bill' and not row['bill']:
            continue
        group = row['bill_key'] if group_by == 'bill' else row[group_by]
        groups[group, row['party']].append(row)
    result = []
    for (group, party), rows in sorted(groups.items()):
        voted = [r for r in rows if r['yea'] + r['nay']]
        eligible = [r for r in voted if r['yea'] != r['nay']]
        dissent = sum(min(r['yea'], r['nay']) > 0 for r in eligible)
        minority = sum(min(r['yea'], r['nay']) for r in eligible)
        members = sum(r['yea'] + r['nay'] for r in eligible)
        result.append(dict(group=group, party=party,
            selected_divisions=len(rows), bills=len({r['bill_key'] for r in rows if r['bill']}),
            eligible_divisions=len(eligible), dissenting_divisions=dissent,
            dissent_frequency_pct=100*dissent/len(eligible) if eligible else None,
            minority_member_votes=minority, eligible_member_votes=members,
            dissent_intensity_pct=100*minority/members if members else None,
            rice_divisions=len(voted),
            mean_rice=100*sum(abs(r['yea']-r['nay'])/(r['yea']+r['nay']) for r in voted)/len(voted) if voted else None))
    return result


def matches(meta, detail, args):
    key = f"{meta['session']}/{meta['bill_number']}"
    return ((not args.bill or key in args.bill)
        and (not args.category or meta['category'] in args.category)
        and (not args.bill_type or detail.get('type', 'Unknown') in args.bill_type)
        and (not args.keyword or any(k.casefold() in
             (detail.get('title', '')+' '+meta['subject']).casefold() for k in args.keyword)))


def write_csv(path, rows):
    with path.open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)


def plot(rows, output, caption):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    groups = sorted({r['group'] for r in rows})
    if len(groups) > 30:
        return 'Chart omitted above 30 groups; narrow the selection or use summary.csv.'
    fig, axes = plt.subplots(1, len(TRACKED), figsize=(16, max(4, len(groups)*.35)), sharey=True)
    for ax, party in zip(axes, TRACKED):
        values = {r['group']: r for r in rows if r['party'] == party}
        for i, group in enumerate(groups):
            r = values[group]
            value = r['dissent_frequency_pct']
            if value is not None:
                ax.barh(i, value, color=PARTY_COLORS[party])
            label = f"{r['dissenting_divisions']}/{r['eligible_divisions']}" if value is not None else 'No majority'
            ax.text((value or 0)+2, i, label, va='center', fontsize=8)
        ax.set_title(party, fontsize=10)
        ax.set_xlim(0, 125)
        ax.set_xticks([0, 50, 100])
        ax.set_xlabel('Divisions with dissent (%)')
    axes[0].set_yticks(range(len(groups)), groups)
    axes[0].invert_yaxis()
    fig.suptitle('How often does anyone vote against their party majority?')
    import textwrap
    fig.text(.5, .015, textwrap.fill(caption, 170), ha='center', fontsize=8)
    fig.tight_layout(rect=(0,.09,1,1))
    fig.savefig(output/'dissent.png', dpi=140)
    plt.close(fig)
    return 'dissent.png'


def run(args):
    sessions = [s for s in SESSIONS if (not args.session or s in args.session)
                and (not args.parliament or int(s.split('-')[0]) in args.parliament)]
    if not sessions:
        raise ValueError('No sessions selected')
    require_valid_corpus(sessions=sessions)
    selected, observations, files = [], [], set()
    for session in sessions:
        directory = ROOT/f'Parliament_{session}'
        metadata = bill_info.load_vote_metadata(directory)
        details = bill_info.load_bill_types(session)
        files.add(directory/'votes_metadata.csv')
        xml = ROOT/'House of Commons'/f'{session}.xml'
        if not xml.exists():
            xml = ROOT/'data'/'sources'/f'legisinfo-{session}-current.xml.gz'
        if xml.exists():
            files.add(xml)
        for number, meta in sorted(metadata.items()):
            detail = details.get(meta['bill_number'], {})
            if not matches(meta, detail, args):
                continue
            path = directory/f'file_{number}.csv'
            files.add(path)
            rows = read_vote_rows(path)
            record = dict(session=session, parliament=int(session.split('-')[0]), division=number,
                date=meta['date'], bill=meta['bill_number'],
                bill_key=f"{session}/{meta['bill_number']}" if meta['bill_number'] else '',
                bill_type=detail.get('type', 'Unknown'), category=meta['category'], stage=meta['stage'] or '',
                title=detail.get('title', ''), subject=meta['subject'],
                yeas=int(meta['yeas']), nays=int(meta['nays']), paired=int(meta['paired']),
                correction=f'{session}/{number}' if f'{session}/{number}' in decisions() else '',
                source_url=f'https://www.ourcommons.ca/members/en/votes/{session.replace("-", "/")}/{number}')
            selected.append(record)
            for party, (yea, nay) in party_counts(rows).items():
                observations.append({**record, 'party': party, 'yea': yea, 'nay': nay})
    if not selected:
        raise ValueError('No matching divisions; check bill keys, type, category or keywords')
    if args.bill:
        missing = set(args.bill)-{r['bill_key'] for r in selected}
        if missing:
            raise ValueError(f'Requested bills have no matching recorded votes: {sorted(missing)}')
    summary = summarize(observations, args.group_by)
    if not summary:
        raise ValueError('No numbered bills in selection; choose another grouping')
    # Exclusive output prevents old files being mistaken for a new result.
    args.output.mkdir(parents=True, exist_ok=False)
    write_csv(args.output/'divisions.csv', selected)
    write_csv(args.output/'party_votes.csv', observations)
    write_csv(args.output/'summary.csv', summary)
    fields = ['session', 'division', 'member_id', 'member', 'raw_party', 'party', 'vote', 'paired', 'binary_vote', 'correction']
    with (args.output/'members.csv.gz').open('wb') as raw:
        import io
        with gzip.GzipFile(fileobj=raw, mode='wb', filename='', mtime=0) as zipped:
            with io.TextIOWrapper(zipped, encoding='utf-8', newline='') as stream:
                writer = csv.DictWriter(stream, fieldnames=fields, lineterminator='\n')
                writer.writeheader()
                for r in selected:
                    for m in read_vote_rows(ROOT/f"Parliament_{r['session']}"/f"file_{r['division']}.csv"):
                        writer.writerow(dict(session=r['session'], division=r['division'], member_id=m['member_id'],
                            member=m['member'], raw_party=m['party'], party=analytic_party(m['party']),
                            vote=m['vote'], paired=m['paired'], binary_vote=binary_vote(m) or '', correction=r['correction']))
    files.update(ROOT/p for p in ['data/corrections/data_decisions.json', 'data/corrections/derived/42-1-871.csv'])
    # Portable hashes cover the selected source tables, corrections and code.
    files.update(ROOT.glob('*.py'))
    hashes = {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes() if p.suffix=='.gz' else p.read_bytes().replace(b'\r\n', b'\n')).hexdigest() for p in sorted(files)}
    manifest = dict(schema_version=1, sessions=sessions, selection={k:str(v) if isinstance(v,Path) else v for k,v in vars(args).items() if k!='output'},
        divisions=len(selected), input_sha256=hashes, chart=plot(summary,args.output, 'Sessions: '+', '.join(sessions)+f'. {len(selected)} selected divisions; all matching stages, including free votes.'+(' 45-1 is incomplete.' if '45-1' in sessions else '')),
        scope='All matching divisions; free-vote stages included. Dissent is not a verified whip breach.')
    (args.output/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n', encoding='utf-8')
    print(f'{len(selected)} divisions; {len(summary)} comparison rows written to {args.output}')
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    scope = parser.add_mutually_exclusive_group()
    scope.add_argument('--session', nargs='+', choices=SESSIONS)
    scope.add_argument('--parliament', nargs='+', type=int, choices=sorted({int(s.split('-')[0]) for s in SESSIONS}))
    parser.add_argument('--bill', nargs='+', help='Session/bill keys, e.g. 42-1/C-89 42-1/C-14')
    parser.add_argument('--category', nargs='+', help='Business category, e.g. government_bill')
    parser.add_argument('--bill-type', nargs='+', help='Exact LEGISinfo type, e.g. "House Government Bill"')
    parser.add_argument('--keyword', nargs='+', help='Case-insensitive title/subject substrings; any keyword matches')
    parser.add_argument('--group-by', choices=['parliament','session','bill','category','bill_type'], default='parliament')
    parser.add_argument('--output', type=Path, required=True, help='New output directory')
    args = parser.parse_args()
    try:
        run(args)
    except (ValueError, OSError) as error:
        parser.exit(1, f'Analysis failed: {error}\n')


if __name__ == '__main__':
    main()

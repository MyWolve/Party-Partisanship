"""Recover official bill/sponsor links from archived sponsor-filter responses.

Only --fetch uses the network. The session-wide export omits sponsor fields;
the official sponsor index and sponsor-filtered bill lists retain the relation.
No name matching assigns identifiers and no historical event dates are inferred.
"""
import argparse
from collections import defaultdict
from datetime import datetime, timezone
import gzip
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sys
import tempfile
import unicodedata

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from can_scrape import fetch
from check_data import SESSIONS
from bill_data import parse_bill_xml, parse_bill_detail, xml_text
from experiment_io import write_csv, write_json
from provenance import verify_inputs
from vote_data import read_vote_rows

# Published facet counts exceed the actual sponsor-filtered results for these
# six historical pairs. Preserve exact discrepancies; do not relax coverage.
# Values are (index count, filtered count), confirmed by session-specific GETs.
INDEX_COUNT_EXCEPTIONS = {
    ('38-1', '212'): (4, 2), ('38-1', '218'): (5, 1),
    ('39-1', '259'): (20, 1), ('39-2', '259'): (19, 1),
    ('40-2', '218'): (5, 1), ('40-3', '218'): (3, 1),
}


def normalized_name(label):
    """Comparison only. Never assign an identifier using this normalization."""
    label = re.sub(r'^(?:(?:Rt\.?\s+Hon\.?|Right Honourable|Hon\.?|Sen\.?|Senator)\s+)+', '', label)
    if ',' in label:
        last, first = label.split(',', 1)
        label = first + ' ' + last
    label = unicodedata.normalize('NFKD', label).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]', '', label)


class SponsorIndex(HTMLParser):
    def __init__(self):
        super().__init__()
        self.people = {}
        self.label = None
        self.text = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'input' and attrs.get('data-input') == 'sponsor':
            person, name = attrs.get('data-value', ''), attrs.get('data-label', '')
            if not person.isdigit() or int(person) <= 0 or not name:
                raise ValueError('Invalid/duplicate sponsor index identity')
            if person in self.people:
                previous = self.people[person]
                # The 44-1 index splits Fortin's bills between two spacing
                # variants of the same Person ID. Preserve both labels and
                # add their disjoint counts; the filtered list verifies the sum.
                if name in previous['aliases'] or re.sub(r'\s', '', name) != re.sub(r'\s', '', previous['name']):
                    raise ValueError('Conflicting duplicate sponsor index identity')
                previous['aliases'].append(name)
            else:
                self.people[person] = {'name': name, 'aliases': [name], 'count': 0}
        if tag == 'label' and attrs.get('for') in self.people:
            self.label, self.text = attrs['for'], []

    def handle_data(self, data):
        if self.label:
            self.text.append(data)

    def handle_endtag(self, tag):
        if tag == 'label' and self.label:
            counts = re.findall(r'(\d+)\s+results?', ' '.join(self.text))
            if len(counts) != 1 or int(counts[0]) <= 0:
                raise ValueError('Missing/invalid sponsor result count')
            self.people[self.label]['count'] += int(counts[0])
            self.label = None


def parse_index(data):
    parser = SponsorIndex()
    parser.feed(data.decode('utf-8-sig'))
    if not parser.people or any(not r['count'] for r in parser.people.values()):
        raise ValueError('Incomplete or empty sponsor index')
    return parser.people


def parse_filtered(data):
    rows = json.loads(data.decode('utf-8-sig'))
    if not isinstance(rows, list) or not rows:
        raise ValueError('Expected nonempty filtered bill list')
    result = {}
    for r in rows:
        session = f"{r['ParliamentNumber']}-{r['SessionNumber']}"
        number = r['NumberCode']
        key = session, number
        if (not re.fullmatch(r'[1-9]\d*-[1-9]\d*', session)
                or not re.fullmatch(r'[CS]-[1-9]\d*[A-Z]?', number)
                or key in result or type(r['Id']) is not int or r['Id'] <= 0
                or r['OriginatingChamberOrganizationId'] not in (1, 2)):
            raise ValueError('Invalid/duplicate filtered bill')
        result[key] = r
    return result


def archived(root, name):
    ledger = json.loads((root/'evidence/sources.json').read_text(encoding='utf-8'))
    data = (root/'evidence'/name).read_bytes()
    entry = ledger[name]
    if hashlib.sha256(data).hexdigest() != entry['sha256']:
        raise ValueError(f'Archived sponsor source changed: {name}')
    content = gzip.decompress(data)
    if hashlib.sha256(content).hexdigest() != entry['response_sha256']:
        raise ValueError(f'Sponsor response content changed: {name}')
    return content


def retrieve(root, name, url, validate):
    path = root/'evidence'/name
    ledger_path = root/'evidence/sources.json'
    ledger = json.loads(ledger_path.read_text(encoding='utf-8'))
    if path.exists():
        if ledger.get(name, {}).get('url') != url:
            raise ValueError(f'Existing sponsor URL differs: {name}')
        data = archived(root, name)
        validate(data)
        return data
    response = fetch(url)
    validate(response.content)
    packed = gzip.compress(response.content, mtime=0)
    path.write_bytes(packed)
    ledger[name] = dict(url=url, resolved_url=response.url,
        retrieved_date=datetime.now(timezone.utc).date().isoformat(),
        sha256=hashlib.sha256(packed).hexdigest(),
        response_sha256=hashlib.sha256(response.content).hexdigest(),
        archive_encoding='gzip', http_status=response.status_code,
        content_type=response.headers.get('Content-Type', ''))
    write_json(ledger_path, ledger)
    return response.content


def fetch_sources(root=ROOT):
    people = set()
    for session in SESSIONS:
        data = retrieve(root, f'sponsors-index-{session}.html.gz',
            f'https://www.parl.ca/legisinfo/en/bills?parlsession={session}', parse_index)
        people.update(parse_index(data))
    print(f'Sponsor index: {len(people)} people across {len(SESSIONS)} sessions', flush=True)
    for i, person in enumerate(sorted(people, key=int), 1):
        retrieve(root, f'sponsors-person-{person}.json.gz',
            f'https://www.parl.ca/legisinfo/en/bills/json?parlsession=all&sponsor={person}', parse_filtered)
        if i % 25 == 0 or i == len(people):
            print(f'Archived sponsor membership {i}/{len(people)}', flush=True)
    for session, person in INDEX_COUNT_EXCEPTIONS:
        retrieve(root, f'sponsors-exception-{session}-{person}.json.gz',
            f'https://www.parl.ca/legisinfo/en/bills/json?parlsession={session}&sponsor={person}', parse_filtered)
    rows = build(root, check_details=False)
    selected = detail_selection(rows)
    for i, r in enumerate(selected, 1):
        session, bill = r['session'], r['bill']
        retrieve(root, detail_filename(r),
            f'https://www.parl.ca/legisinfo/en/bill/{session}/{bill.lower()}/json',
            lambda data: parse_bill_detail(data, session, bill))
        if i % 25 == 0 or i == len(selected):
            print(f'Archived direct sponsor detail {i}/{len(selected)}', flush=True)


def detail_filename(row):
    return f"sponsors-detail-{row['session']}-{row['bill']}.json.gz"


def detail_selection(rows):
    selected = {}
    first = set()
    for r in rows:
        group = r['session'], r['originating_chamber']
        if (group not in first or r['session'] == '40-1' or r['archived_name_comparison'] == 'different_label'
                or (r['session'], r['sponsor_person_id']) in INDEX_COUNT_EXCEPTIONS):
            selected[r['session'], r['bill']] = r
        first.add(group)
    return [selected[k] for k in sorted(selected)]


def build(root=ROOT, include_review=False, check_details=True):
    indexes = {s: parse_index(archived(root, f'sponsors-index-{s}.html.gz')) for s in SESSIONS}
    people = set().union(*(set(index) for index in indexes.values()))
    bills = {}
    for session in SESSIONS:
        path = root/'House of Commons'/f'{session}.xml'
        baseline = parse_bill_xml(path.read_bytes(), session) if path.exists() else {}
        current = parse_bill_xml((root/'evidence'/f'legisinfo-{session}-current.xml').read_bytes(), session)
        for number, r in current.items():
            bills[session, number] = dict(type=r['type'], title=r['title'],
                archived_sponsor=baseline.get(number, {}).get('sponsor', ''))
    memberships = defaultdict(list)
    counts = []
    for person in sorted(people, key=int):
        name = f'sponsors-person-{person}.json.gz'
        records = parse_filtered(archived(root, name))
        for session in SESSIONS:
            selected = {k: r for k, r in records.items() if k[0] == session}
            expected = indexes[session].get(person, {}).get('count', 0)
            if len(selected) != expected:
                if INDEX_COUNT_EXCEPTIONS.get((session, person)) != (expected, len(selected)):
                    raise ValueError(f'Sponsor index/filter count differs: {session}/{person}: {len(selected)} != {expected}')
                specific = parse_filtered(archived(root, f'sponsors-exception-{session}-{person}.json.gz'))
                if set(specific) != set(selected):
                    raise ValueError('Session-specific sponsor filter differs from all-session results')
            if expected or selected:
                counts.append(dict(session=session, person_id=person, index_count=expected,
                    filtered_count=len(selected), status='match' if len(selected) == expected else 'documented_index_overcount'))
            for key, r in selected.items():
                if key not in bills:
                    raise ValueError(f'Sponsor filter returned bill outside frozen universe: {key}')
                if xml_text(r['LongTitleEn']) != bills[key]['title'] or r['BillDocumentTypeNameEn'] != bills[key]['type']:
                    raise ValueError(f'Sponsor bill title/type changed: {key}')
                if r.get('SponsorPersonId') not in (None, int(person)):
                    raise ValueError(f'Sponsor filter conflicts with embedded Person ID: {key}')
                memberships[key].append(dict(person_id=person, name=indexes[session][person]['name'],
                    aliases=indexes[session][person]['aliases'],
                    chamber='House' if r['OriginatingChamberOrganizationId'] == 1 else 'Senate',
                    bill_id=r['Id'], source_file=f'evidence/{name}',
                    index_source=f'evidence/sponsors-index-{session}.html.gz'))
    observed = defaultdict(set)
    for session in SESSIONS:
        for path in (root/f'Parliament_{session}').glob('file_*.csv'):
            observed[session].update(r['member_id'] for r in read_vote_rows(path))
    rows = []
    for (session, number), bill in sorted(bills.items()):
        matched = memberships[session, number]
        if len(matched) != 1:
            raise ValueError(f'Expected exactly one sponsor: {session}/{number}: {matched}')
        r = matched[0]
        rows.append(dict(session=session, bill=number, bill_id=r['bill_id'],
            sponsor_person_id=r['person_id'], sponsor_name=r['name'], originating_chamber=r['chamber'],
            sponsor_index_aliases=json.dumps(r['aliases'], ensure_ascii=False),
            archived_sponsor=bill['archived_sponsor'],
            archived_name_comparison=('not_archived' if not bill['archived_sponsor'] else
                'normalized_agreement' if any(normalized_name(bill['archived_sponsor']) == normalized_name(n)
                                            for n in r['aliases']) else 'different_label'),
            observed_in_session_votes=r['person_id'] in observed[session],
            identity_method='official_sponsor_filter', temporal_scope='bill_record_at_retrieval',
            source_file=r['source_file'], index_source=r['index_source'], detail_source=''))
    if check_details:
        for r in detail_selection(rows):
            name = detail_filename(r)
            detail = parse_bill_detail(archived(root, name), r['session'], r['bill'])
            if (detail['sponsor_person_id'] != r['sponsor_person_id'] or detail['bill_id'] != r['bill_id']
                    or detail['originating_chamber'] != r['originating_chamber']):
                raise ValueError(f'Direct sponsor detail disagrees with filter membership: {name}')
            r['detail_source'] = f'evidence/{name}'
    return (rows, counts) if include_review else rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fetch', action='store_true')
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    if args.fetch:
        fetch_sources()
        return
    verify_inputs()
    rows, counts = build(include_review=True)
    with tempfile.TemporaryDirectory() as name:
        path = Path(name)/'bill_sponsors.csv'
        write_csv(path, rows)
        saved = ROOT/'audit/sponsors/bill_sponsors.csv'
        if args.check:
            if path.read_bytes() != saved.read_bytes():
                raise ValueError('Saved sponsor mapping changed')
        else:
            saved.parent.mkdir(parents=True, exist_ok=True)
            saved.write_bytes(path.read_bytes())
        count_path = Path(name)/'index_counts.csv'
        write_csv(count_path, counts)
        saved_counts = saved.with_name('index_counts.csv')
        if args.check:
            if count_path.read_bytes() != saved_counts.read_bytes():
                raise ValueError('Saved sponsor index review changed')
        else:
            saved_counts.write_bytes(count_path.read_bytes())
    print(f'Recovered {len(rows)} bill sponsors without name-based identity inference')


if __name__ == '__main__':
    main()

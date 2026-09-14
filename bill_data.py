"""Strict adapters for the archived and current LEGISinfo XML schemas."""
import re
import json
import xml.etree.ElementTree as ET

TYPES={'House Government Bill', 'Senate Government Bill', 'Private Member’s Bill',
       "Private Member's Bill", 'Senate Public Bill', 'Senate Private Bill'}


def xml_text(value):
    """Match XML's newline normalization and this adapter's outer trimming."""
    return value.replace('\r\n', '\n').replace('\r', '\n').strip()


def parse_bill_detail(data, session, number):
    """The per-bill JSON supplies sponsor IDs absent from bulk exports."""
    records = json.loads(data)
    if not isinstance(records, list) or len(records) != 1:
        raise ValueError('Expected exactly one detailed bill')
    r = records[0]
    if (f"{r.get('ParliamentNumber')}-{r.get('SessionNumber')}" != session
            or r.get('NumberCode') != number):
        raise ValueError('Wrong detailed bill/session')
    person = r.get('SponsorPersonId')
    name = (r.get('SponsorPersonName') or '').strip()
    if type(person) is not int or person <= 0 or not name:
        raise ValueError('Missing detailed sponsor identity')
    if (r.get('BillDocumentTypeNameEn') not in TYPES or not r.get('LongTitleEn')
            or type(r.get('Id')) is not int or r['Id'] <= 0
            or r.get('OriginatingChamberOrganizationId') != (1 if number.startswith('C-') else 2)):
        raise ValueError('Invalid detailed bill metadata')
    return dict(bill=number, bill_id=r['Id'], type=r['BillDocumentTypeNameEn'], title=xml_text(r['LongTitleEn']),
        sponsor=name, sponsor_person_id=str(person),
        originating_chamber='House' if r['OriginatingChamberOrganizationId'] == 1 else 'Senate',
        sponsor_senate_affiliation_id=r.get('SponsorSenateSystemAffiliationId'),
        sponsor_role=(r.get('SponsorAffiliationTitleEn') or '').strip(),
        temporal_scope='bill_record_at_retrieval')

def parse_bill_xml(data, session):
    root=ET.fromstring(data)
    if root.tag!='Bills' or not len(root): raise ValueError('Expected nonempty Bills XML')
    result={}
    for bill in root:
        if bill.tag!='Bill': raise ValueError('Unexpected bill element')
        tags=[c.tag for c in bill]
        if len(tags)!=len(set(tags)): raise ValueError('Duplicate bill fields')
        archived=bill.find('BillNumberFormatted') is not None
        current=bill.find('NumberCode') is not None
        if archived==current: raise ValueError('Unknown or ambiguous bill schema')
        number=(bill.findtext('BillNumberFormatted' if archived else 'NumberCode') or '').strip()
        actual=f"{bill.findtext('ParliamentNumber')}-{bill.findtext('SessionNumber')}"
        if actual!=session: raise ValueError(f'Wrong bill session: {actual}, expected {session}')
        if not re.fullmatch(r'[CS]-[1-9]\d*[A-Z]?',number) or number in result:
            raise ValueError(f'Missing, invalid or duplicate bill number: {number}')
        kind=(bill.findtext('BillTypeEn' if archived else 'BillDocumentTypeNameEn') or '').strip()
        title=(bill.findtext('LongTitleEn') or '').strip()
        if kind not in TYPES or not title: raise ValueError(f'Missing/unknown type or title: {number}')
        result[number]={'type':kind,'sponsor':(bill.findtext('SponsorEn' if archived else 'SponsorPersonName') or '').strip(), 'title':title}
    return result

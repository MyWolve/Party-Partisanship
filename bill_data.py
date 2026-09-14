"""Strict adapters for the archived and current LEGISinfo XML schemas."""
import re
import xml.etree.ElementTree as ET

TYPES={'House Government Bill', 'Senate Government Bill', 'Private Member’s Bill',
       "Private Member's Bill", 'Senate Public Bill', 'Senate Private Bill'}


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
        result[number]={'type':kind.replace('’', "'"),'sponsor':(bill.findtext('SponsorEn' if archived else 'SponsorPersonName') or '').strip(), 'title':title}
    return result

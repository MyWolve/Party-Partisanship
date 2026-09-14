"""Sponsor identity comes from official IDs/filter membership, never fuzzy names."""
import json
import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch
from tools.recover_sponsors import parse_index, parse_filtered, normalized_name
from bill_data import parse_bill_detail
from tools.collect_bills import collect


def detail(**changes):
    row = dict(ParliamentNumber=40, SessionNumber=1, NumberCode='C-2', Id=12,
               OriginatingChamberOrganizationId=1, SponsorPersonId=1792,
               SponsorPersonName='Stockwell Day', LongTitleEn='Example bill',
               BillDocumentTypeNameEn='House Government Bill', SponsorSenateSystemAffiliationId=None)
    row.update(changes)
    return json.dumps([row]).encode()


class Response:
    status_code = 200
    headers = {'Content-Type': 'application/json'}
    url = 'https://www.parl.ca/example'
    def __init__(self, content):
        self.content = content


def index(person='1', name='Smith, Anne', count=2):
    return (f'<input data-input="sponsor" data-value="{person}" data-label="{name}">'
            f'<label for="{person}">{name}<span>{count}<span> results</span></span></label>')


class SponsorTests(unittest.TestCase):
    def test_json_title_normalizes_only_xml_newlines_and_outer_space(self):
        r = parse_bill_detail(detail(LongTitleEn='A\r\nB\r\n'), '40-1', 'C-2')
        self.assertEqual(r['title'], 'A\nB')
        self.assertEqual(parse_bill_detail(detail(LongTitleEn='A  B'), '40-1', 'C-2')['title'], 'A  B')

    def test_detailed_identity_and_namespace(self):
        self.assertEqual(parse_bill_detail(detail(), '40-1', 'C-2')['sponsor_person_id'], '1792')
        for kwargs in [dict(SponsorPersonId=None), dict(SponsorPersonId=True),
                       dict(SponsorPersonName=''), dict(NumberCode='C-3'), dict(SessionNumber=2)]:
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                parse_bill_detail(detail(**kwargs), '40-1', 'C-2')
        r = parse_bill_detail(detail(NumberCode='S-1', OriginatingChamberOrganizationId=2,
            SponsorPersonId=1861, SponsorSenateSystemAffiliationId=59), '40-1', 'S-1')
        self.assertEqual(r['sponsor_person_id'], '1861')
        self.assertEqual(r['sponsor_senate_affiliation_id'], 59)

    def test_sponsor_collection_retains_identity_and_rejects_wrong_detail(self):
        xml = b'<Bills><Bill><NumberCode>C-2</NumberCode><ParliamentNumber>40</ParliamentNumber><SessionNumber>1</SessionNumber><BillDocumentTypeNameEn>House Government Bill</BillDocumentTypeNameEn><LongTitleEn>Example bill</LongTitleEn></Bill></Bills>'
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            with patch('tools.collect_bills.fetch', side_effect=[Response(xml), Response(detail())]):
                result = collect('40-1', root/'good', root=root, with_sponsors=True)
            self.assertEqual(result['sponsor_identity_records'], 1)
            recovered = json.loads((root/'good/bill_sponsors.json').read_text())
            self.assertEqual(recovered['C-2']['sponsor_person_id'], '1792')
            with patch('tools.collect_bills.fetch', side_effect=[Response(xml), Response(detail(NumberCode='C-3'))]):
                with self.assertRaisesRegex(ValueError, 'Wrong detailed'):
                    collect('40-1', root/'bad', root=root, with_sponsors=True)
            failed = json.loads((root/'bad/collection_manifest.json').read_text())
            self.assertEqual(failed['status'], 'failed')
            self.assertTrue((root/'bad/details/C-2.json').exists())

    def test_index_identity_and_count(self):
        p = parse_index(index().encode())
        self.assertEqual(p['1']['name'], 'Smith, Anne')
        self.assertEqual(p['1']['count'], 2)

    def test_same_id_spacing_variant_preserves_aliases_and_count(self):
        p = parse_index((index(name='Fortin, Rhéal Éloi', count=1)
                         + index(name='Fortin, RhéalÉloi', count=1)).encode())
        self.assertEqual(p['1']['count'], 2)
        self.assertEqual(len(p['1']['aliases']), 2)

    def test_index_rejects_missing_duplicate_or_conflicting_identity(self):
        for data in ['<html>error</html>', index(person='0'), index(count=0),
                     index()+index(), index()+index(name='Jones, Bob'),
                     '<input data-input="sponsor" data-value="1" data-label="Smith">']:
            with self.subTest(data=data), self.assertRaises(ValueError):
                parse_index(data.encode())

    def test_filtered_list_rejects_duplicate_and_wrong_shape(self):
        r = dict(ParliamentNumber=40, SessionNumber=1, NumberCode='C-2', Id=12,
                 OriginatingChamberOrganizationId=1)
        self.assertIn(('40-1', 'C-2'), parse_filtered(json.dumps([r]).encode()))
        for value in [[], {}, [r, r], [dict(r, Id=0)], [dict(r, NumberCode='garbage')]]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                parse_filtered(json.dumps(value).encode())

    def test_name_comparison_is_conservative(self):
        self.assertEqual(normalized_name('Hon. Stockwell Day'), normalized_name('Day, Stockwell'))
        self.assertNotEqual(normalized_name('Peter Gordon MacKay'), normalized_name('MacKay, Peter'))


if __name__ == '__main__':
    unittest.main()

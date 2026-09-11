"""Schema adapters and identity reconciliation contracts."""
import collections
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from bill_data import parse_bill_xml
from tools.collect_bills import collect, compare_bills
from tools.reconcile_members import match_member, reconcile


def bill_xml(current=False, session='40-1', number='C-1'):
    p,s=session.split('-')
    number_tag='NumberCode' if current else 'BillNumberFormatted'
    kind='BillDocumentTypeNameEn' if current else 'BillTypeEn'
    sponsor='SponsorPersonName' if current else 'SponsorEn'
    return f'<Bills><Bill><{number_tag}>{number}</{number_tag}><{kind}>House Government Bill</{kind}><{sponsor}>A</{sponsor}><LongTitleEn>Title</LongTitleEn><ParliamentNumber>{p}</ParliamentNumber><SessionNumber>{s}</SessionNumber></Bill></Bills>'.encode()

class BillSchemaTests(unittest.TestCase):
    def test_both_schemas_agree(self):
        self.assertEqual(parse_bill_xml(bill_xml(),'40-1'),parse_bill_xml(bill_xml(True),'40-1'))
    def test_split_bill_suffix(self):
        self.assertIn('C-23A',parse_bill_xml(bill_xml(number='C-23A'),'40-1'))
    def test_invalid_schemas_and_wrong_session(self):
        for data in [b'<Bills/>',b'<html/>',bill_xml(session='40-2'),bill_xml().replace(b'</Bill>',b'<BillTypeEn>Other</BillTypeEn></Bill>'),bill_xml().replace(b'House Government Bill',b'New unknown type')]:
            with self.subTest(data=data),self.assertRaises(ValueError):parse_bill_xml(data,'40-1')
    def test_refresh_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as d,patch('tools.collect_bills.fetch') as fetch:
            with self.assertRaises(FileExistsError):collect('40-1',d)
            fetch.assert_not_called()
    def test_invalid_refresh_retains_failure(self):
        with tempfile.TemporaryDirectory() as d:
            source=Path(d)/'invalid.xml';source.write_text('<html/>');out=Path(d)/'new'
            with self.assertRaises(ValueError):collect('40-1',out,source)
            self.assertEqual(json.loads((out/'collection_manifest.json').read_text())['status'],'failed')
    def test_lost_sponsor_is_a_change(self):
        old={'C-1':{'sponsor':'A','type':'House Government Bill','title':'Title'}}
        new={'C-1':{**old['C-1'],'sponsor':''}}
        self.assertEqual(compare_bills(old,new)[0]['kind'],'changed')

class ReconciliationTests(unittest.TestCase):
    def indexes(self):return {key:collections.defaultdict(set) for key in ('full_name','surname_constituency','first_surname')}
    def test_same_name_requires_constituency(self):
        idx=self.indexes();idx['full_name']['davidanderson']={'1','2'};idx['surname_constituency'][('anderson','victoria')]={'2'}
        self.assertEqual(match_member('ANDERSON, David','Victoria',idx),('2','surname_constituency'))
        with self.assertRaises(ValueError):match_member('ANDERSON, David','Unknown',idx)
    def test_middle_name_fallback(self):
        idx=self.indexes();idx['first_surname'][('steven','fletcher')]={'3'}
        self.assertEqual(match_member('FLETCHER, Steven John','Riding',idx),('3','first_surname'))
    def test_real_record_level_discrepancy_stays_visible(self):
        crosswalk,differences,summary,dates=reconcile()
        self.assertEqual(sum(r['divisions'] for r in summary),933)
        self.assertEqual(sum(r['joined_records'] for r in summary),256676)
        self.assertEqual([(r['session'],r['division'],r['person_id'],r['issue']) for r in differences],[('40-2',157,'608','deposit_only_observation')])
        self.assertEqual([r['division_id'] for r in dates if not r['date_matches']],['H38S1V153'])
        self.assertTrue(all(r['observable_records']==0 for r in crosswalk if not r['person_id']))

if __name__=='__main__':unittest.main()

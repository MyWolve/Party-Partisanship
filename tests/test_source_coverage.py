"""Later-session source sample and reviewed bill supplement checks."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET
import bill_info
from tools.review_source_coverage import parse_vote_xml, build, ROOT

class CoverageTests(unittest.TestCase):
    def fixture(self):
        root=ET.parse(ROOT/'evidence/review-45-1-1.xml').getroot()
        return root,root[0]
    def test_xml_rejects_wrong_division_and_flags(self):
        root,row=self.fixture()
        with self.assertRaisesRegex(ValueError,'Wrong vote'):parse_vote_xml(ET.tostring(root),'45-1',2)
        row.find('IsVoteYea').text='maybe'
        with self.assertRaisesRegex(ValueError,'flag'):parse_vote_xml(ET.tostring(root),'45-1',1)
    def test_xml_rejects_duplicate_missing_and_html(self):
        root,row=self.fixture();root.append(row)
        with self.assertRaisesRegex(ValueError,'duplicate'):parse_vote_xml(ET.tostring(root),'45-1',1)
        root,row=self.fixture();row.remove(row.find('PersonId'))
        with self.assertRaisesRegex(ValueError,'Incomplete'):parse_vote_xml(ET.tostring(root),'45-1',1)
        with self.assertRaises(ValueError):parse_vote_xml(b'<html/>','45-1',1)
    def test_real_sample_and_type_upgrade(self):
        coverage,changes,votes,differences,classification=build()
        self.assertEqual(len(votes),35)
        self.assertEqual(sum(r['matching_observations'] for r in votes),10178)
        self.assertEqual(differences,[])
        self.assertTrue(all(r['date_matches'] and r['result_matches'] for r in votes))
        self.assertEqual(sum(r['lost_sponsors'] for r in coverage),4411)
        self.assertTrue(all(r['before_category']==r['after_category'] for r in classification))
        self.assertEqual(sum(r['before_source']!=r['after_source'] for r in classification),107)
    def test_45_supplement_is_used(self):
        bills=bill_info.load_bill_types('45-1')
        self.assertEqual(len(bills),185)
        self.assertEqual(bill_info.classify_vote('Bill C-201','C-201',bills)['bill_type_source'],'legisinfo')
    def test_missing_supplement_cannot_silently_revert(self):
        with tempfile.TemporaryDirectory() as d,patch.object(bill_info,'PROJECT_ROOT',d),patch.object(bill_info,'BILL_XML_DIR',d):
            with self.assertRaises(FileNotFoundError):bill_info.load_bill_types('45-1')

if __name__=='__main__':unittest.main()

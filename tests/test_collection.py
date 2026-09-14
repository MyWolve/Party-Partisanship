"""Collection failures and legacy entry-point regressions, with no network."""
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import can_scrape as collect
import visualize_parliament as visual
from vote_data import parse_vote_text

CSV = b'Person ID,Member of Parliament,Political Affiliation,Member Voted,Paired\n1,A,Liberal,Yea,\n'
def metadata(number='1', yeas='1'):
    values = [number, '2008-11-27T12:00:00', 'Test division', '', 'Agreed To', yeas, '0', '0']
    return ('<Votes><Vote>' + ''.join(f'<{tags[0]}>{value}</{tags[0]}>' for (_, tags), value in zip(collect.METADATA_FIELDS, values)) + '</Vote></Votes>').encode()

def response(data):
    return SimpleNamespace(content=data, url='https://www.ourcommons.ca/test', status_code=200, headers={})

class CollectionTests(unittest.TestCase):
    def test_successful_snapshot_and_receipts(self):
        with tempfile.TemporaryDirectory() as d, patch.object(collect, 'fetch', side_effect=[response(metadata()), response(CSV), response(metadata())]):
            out = Path(d)/'new'
            report = collect.collect_session('40-1', out)
            self.assertEqual(report['status'], 'validated_raw_snapshot')
            self.assertEqual(len(report['responses']), 3)
            self.assertEqual((out/'Parliament_40-1/file_1.csv').read_bytes(), CSV)

    def test_existing_directory_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as d, patch.object(collect, 'fetch') as fetch:
            marker = Path(d)/'keep'; marker.write_text('original')
            with self.assertRaises(FileExistsError): collect.collect_session('40-1', d)
            fetch.assert_not_called()
            self.assertEqual(marker.read_text(), 'original')

    def test_invalid_session_cannot_create_paths(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)/'new'
            with self.assertRaises(ValueError): collect.collect_session('../main', out)
            self.assertFalse(out.exists())

    def test_bad_downloads_remain_failed_with_raw_evidence(self):
        for data in [b'<html>Error</html>', CSV.splitlines(keepends=True)[0], CSV.replace(b'Yea', b'Nay')]:
            with self.subTest(data=data), tempfile.TemporaryDirectory() as d, patch.object(collect, 'fetch', side_effect=[response(metadata()), response(data)]):
                out = Path(d)/'new'
                with self.assertRaises(ValueError): collect.collect_session('40-1', out)
                report=json.loads((out/'collection_manifest.json').read_text())
                self.assertEqual(report['status'], 'failed')
                self.assertEqual((out/'Parliament_40-1/file_1.csv').read_bytes(), data)

    def test_transport_failure_is_not_reported_as_skipped(self):
        import requests
        with tempfile.TemporaryDirectory() as d, patch.object(collect, 'fetch', side_effect=requests.Timeout('fixture')):
            out=Path(d)/'new'
            with self.assertRaises(requests.Timeout): collect.collect_session('40-1', out)
            self.assertEqual(json.loads((out/'collection_manifest.json').read_text())['status'], 'failed')

    def test_changing_session_fails(self):
        with tempfile.TemporaryDirectory() as d, patch.object(collect, 'fetch', side_effect=[response(metadata()), response(CSV), response(metadata('2'))]):
            with self.assertRaisesRegex(ValueError, 'changed during'): collect.collect_session('40-1', Path(d)/'new')

    def test_bad_metadata_fails_before_members(self):
        for data in [b'<Votes/>', b'<html><body>Error</body></html>', metadata(yeas='-1'), metadata().replace(b'</Votes>', metadata().split(b'<Votes>')[1]), metadata().replace(b'</Vote>', b'<decisiondivisionnumber>2</decisiondivisionnumber></Vote>')]:
            with self.subTest(data=data), self.assertRaises(ValueError): collect.parse_metadata(data)

class LegacyTests(unittest.TestCase):
    def test_identity_survives_display_name_change(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d)/'file_1.csv').write_bytes(CSV)
            (Path(d)/'file_2.csv').write_bytes(CSV.replace(b',A,', b',New name,'))
            bills, labels = visual.load_member_history(d)
            result = visual.mp_loyalty(bills, min_votes=2)
            self.assertEqual(list(result), ['1'])
            self.assertEqual(result['1']['votes'], 2)
            self.assertEqual(labels['1'], 'New name')

    def test_metadata_headers_are_required_and_unique(self):
        import bill_info
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'votes_metadata.csv'
            for header in ['vote_number,date', 'vote_number,date,subject,bill_number,result,yeas,nays,paired,paired']:
                p.write_text(header+'\n')
                with self.assertRaisesRegex(ValueError, 'columns'): bill_info.load_vote_metadata(d)

    def test_exact_division_lookup(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d)/'file_10.csv').write_bytes(CSV.replace(b'Yea', b'Nay'))
            (Path(d)/'file_1.csv').write_bytes(CSV)
            self.assertEqual(visual.load_parliament(d, 'file_1')['Liberal'], [('A', 'Yea')])
            for name in ['file_', 'votes_metadata.csv', '../file_1.csv']:
                with self.assertRaises(ValueError): visual.load_parliament(d, name)

    def test_floor_crossing_and_ties(self):
        def votes(lib, con):
            return {p: lib if p=='Liberal' else con if p=='Conservative' else [] for p in visual.PARTIES}
        bills=[('file_1', votes([('A','Nay'),('B','Yea'),('C','Yea')], [])),
               ('file_2', votes([], [('A','Nay'),('D','Nay'),('E','Yea')])),
               ('file_3', votes([], [('A','Yea'),('D','Nay')]))]
        result=visual.mp_loyalty(bills,min_votes=2)['A']
        self.assertEqual((result['votes'],result['rebellions'],result['loyalty']), (2,1,50.0))

if __name__=='__main__': unittest.main()

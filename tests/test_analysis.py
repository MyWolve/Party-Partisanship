"""Small, hand-calculated metrics and real-data export contracts."""
import csv
import gzip
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from analyze import summarize, matches, party_counts, run
from vote_data import parse_vote_text, tally
from visualize_parliament import rice_index


def row(y, n, bill='C-1', session='38-1'):
    return dict(yea=y, nay=n, party='Liberal', parliament=int(session.split('-')[0]),
                session=session, bill=bill, bill_key=f'{session}/{bill}', category='government_bill')


class MetricsTests(unittest.TestCase):
    def test_hand_calculated_frequency_intensity_rice(self):
        r = summarize([row(3,1), row(2,0), row(1,1), row(0,0)], 'parliament')[0]
        self.assertEqual((r['eligible_divisions'],r['dissenting_divisions']), (2,1))
        self.assertEqual(r['dissent_frequency_pct'],50)
        self.assertAlmostEqual(r['dissent_intensity_pct'],100/6)
        self.assertEqual(r['mean_rice'],50)  # mean of 50, 100, 0; no-vote omitted
        self.assertEqual(rice_index([('a','Yea'),('b','Yea'),('c','Yea'),('d','Nay')]),50)

    def test_empty_majority_is_missing_not_zero(self):
        r = summarize([row(1,1),row(0,0)], 'parliament')[0]
        self.assertIsNone(r['dissent_frequency_pct'])
        self.assertIsNone(r['dissent_intensity_pct'])

    def test_bill_keys_do_not_merge_sessions(self):
        rs=[row(2,1),row(3,0),row(2,1,session='38-2')]
        self.assertEqual([r['selected_divisions'] for r in summarize(rs,'bill')],[2,1])
        self.assertEqual(summarize(rs,'parliament')[0]['selected_divisions'],3)

    def test_unnumbered_business_not_a_bill(self):
        self.assertEqual(summarize([row(2,1,bill='')], 'bill'),[])

    def test_paired_and_dual_flags(self):
        rows=parse_vote_text('Person ID,Member,Affiliation,Voted,Paired\n1,A,Liberal,Yea,\n2,B,Liberal,Yea/Nay,\n3,C,Liberal,Nay,Paired\n')
        self.assertEqual(tally(rows),(2,2,1))
        self.assertEqual(party_counts(rows)['Liberal'],[1,0])

    def test_malformed_and_duplicate_members_fail(self):
        header='Person ID,Member,Affiliation,Voted,Paired\n'
        for text in ['1,A,Liberal,Maybe,\n','1,A,Liberal,Yea,\n1,A,Liberal,Nay,\n','1,A,Liberal\n']:
            with self.assertRaises(ValueError):parse_vote_text(header+text)

    def test_keyword_and_type_intersection(self):
        args=SimpleNamespace(bill=['42-1/C-89'],category=['government_bill'],bill_type=['House Government Bill'],keyword=['POSTAL'])
        meta=dict(session='42-1',bill_number='C-89',category='government_bill',subject='Third reading')
        self.assertTrue(matches(meta,dict(type='House Government Bill',title='Postal services'),args))
        self.assertFalse(matches(meta,dict(type="Private Member's Bill",title='Postal services'),args))
        self.assertFalse(matches({**meta,'session':'43-1'},dict(type='House Government Bill',title='Postal services'),args))

    def test_actual_type_and_free_vote_scope(self):
        import bill_info
        details=bill_info.load_bill_types('42-1')
        self.assertEqual(details['C-89']['type'],'House Government Bill')
        meta=dict(session='42-1',bill_number='C-14',category='government_bill',stage='third_reading')
        self.assertEqual(bill_info.whip_status(meta,'Liberal')['status'],'documented_free')
        self.assertNotEqual(bill_info.whip_status({**meta,'category':'procedural'},'Liberal')['status'],'documented_free')


class ExportTests(unittest.TestCase):
    def test_bill_export_repeat_and_independent_member_readback(self):
        with tempfile.TemporaryDirectory() as tmp:
            args=SimpleNamespace(session=['42-1'],parliament=None,bill=['42-1/C-89'],category=None,bill_type=None,keyword=None,group_by='bill',output=Path(tmp)/'one')
            summary=run(args)
            args.output=Path(tmp)/'two';run(args)
            for name in ['divisions.csv','party_votes.csv','summary.csv','members.csv.gz','manifest.json']:
                self.assertEqual((Path(tmp)/'one'/name).read_bytes(),(args.output/name).read_bytes())
            with gzip.open(args.output/'members.csv.gz','rt',encoding='utf-8') as stream:
                members=list(csv.DictReader(stream))
            with (args.output/'divisions.csv').open(encoding='utf-8') as stream:
                divisions=list(csv.DictReader(stream))
            for d in divisions:
                rows=[r for r in members if r['division']==d['division']]
                self.assertEqual(sum(r['vote'] in ('Yea','Yea/Nay') for r in rows),int(d['yeas']))
                self.assertEqual(sum(r['vote'] in ('Nay','Yea/Nay') for r in rows),int(d['nays']))
                self.assertEqual(sum(r['paired']=='True' for r in rows),int(d['paired']))
            lib=next(r for r in summary if r['party']=='Liberal')
            self.assertEqual((lib['selected_divisions'],lib['dissenting_divisions'],lib['minority_member_votes']),(3,2,11))
            with self.assertRaises(FileExistsError):run(args)

    def test_unmatched_bill_fails_without_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            args=SimpleNamespace(session=['40-1'],parliament=None,bill=['40-1/C-999'],category=None,bill_type=None,keyword=None,group_by='bill',output=Path(tmp)/'none')
            with self.assertRaisesRegex(ValueError,'No matching'):run(args)
            self.assertFalse(args.output.exists())

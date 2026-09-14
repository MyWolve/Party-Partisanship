"""Hand-calculated fixtures and failure-path tests; no network or full scrape."""
import csv
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import bill_info
import check_data
import vote_data
from experiments import experiment_e1 as e1, experiment_e7 as e7
from visualize_parliament import count_yea_nay, rice_index, majority_cohesion, party_majority_side, find_rebels

HEADER = 'Person ID,Member of Parliament,Political Affiliation,Member Voted,Paired\n'


class ParsingTests(unittest.TestCase):
    def test_current_and_legacy_headers(self):
        current = vote_data.parse_vote_text(HEADER + '1,A,Liberal,Yea,\n')[0]
        legacy = vote_data.parse_vote_text('Member,Affiliation,Voted,Paired\nA,Liberal,Yea,\n')[0]
        self.assertEqual(current['member'], legacy['member'])
        self.assertEqual(current['vote'], 'Yea')

    def test_reordered_columns(self):
        row = vote_data.parse_vote_text('Member Voted,Paired,Political Affiliation,Member of Parliament\nNay,,NDP,A\n')[0]
        self.assertEqual((row['member'], row['vote']), ('A', 'Nay'))

    def test_invalid_inputs_fail(self):
        cases = ['garbage\nhello\n', HEADER + '1,A,Liberal,Maybe,\n',
                 HEADER + '1,A,Liberal,Yea,\n1,A,Liberal,Nay,\n',
                 HEADER + '1,A,Liberal\n', HEADER + '1,A,Liberal,,\n',
                 HEADER + '1,A,Liberal,Yea,,extra\n']
        for text in cases:
            with self.subTest(text=text), self.assertRaises(ValueError):
                vote_data.parse_vote_text(text)

    def test_paired_and_dual_flags(self):
        rows = vote_data.parse_vote_text(HEADER + '1,A,Liberal,,Paired\n2,B,NDP,Yea/Nay,\n')
        self.assertEqual(vote_data.tally(rows), (1, 1, 1))
        self.assertEqual(count_yea_nay([(r['member'], r['vote']) for r in rows]), (0, 0))

    def test_text_hash_portable(self):
        self.assertEqual(vote_data.text_hash('a\r\nb\r\n'), vote_data.text_hash('a\nb\n'))
        self.assertNotEqual(vote_data.text_hash('a\nb\n'), vote_data.text_hash('a\nb'))

    def test_paired_binary_combination_is_excluded(self):
        row = vote_data.parse_vote_text(HEADER + '1,A,Liberal,Yea,Paired\n')[0]
        self.assertEqual(vote_data.tally([row]), (1, 0, 1))
        self.assertEqual(vote_data.binary_vote(row), '')
        from visualize_parliament import load_vote_file
        with tempfile.TemporaryDirectory() as d:
            path = Path(d)/'file_1.csv'
            path.write_text(HEADER + '1,A,Liberal,Nay,Paired\n2,B,Liberal,Yea,\n')
            self.assertEqual(rice_index(load_vote_file(path)['Liberal']), 100)

    def test_changed_audited_file_fails(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)/'Parliament_38-1'/'file_159.csv'
            p.parent.mkdir()
            p.write_text(HEADER + '1,A,Liberal,Yea,\n', encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 're-audit'):
                vote_data.read_vote_rows(p)


class MetricTests(unittest.TestCase):
    def test_hand_calculated_3_to_1(self):
        votes = [('a','Yea'), ('b','Yea'), ('c','Yea'), ('d','Nay')]
        self.assertEqual(rice_index(votes), 50)
        self.assertEqual(majority_cohesion(votes), 75)
        self.assertEqual(party_majority_side(votes), 'Yea')
        self.assertEqual(find_rebels({'Liberal': votes}, ['Liberal'])['Liberal'], ['d'])

    def test_tie_and_empty(self):
        self.assertEqual(rice_index([('a','Yea'), ('b','Nay')]), 0)
        self.assertIsNone(party_majority_side([('a','Yea'), ('b','Nay')]))
        self.assertIsNone(rice_index([]))

    def test_dual_excluded_not_arbitrarily_yea(self):
        self.assertEqual(rice_index([('a','Yea/Nay'), ('b','Nay')]), 100)
        self.assertEqual(party_majority_side([('a','Yea/Nay'), ('b','Nay')]), 'Nay')

    def test_small_group_enumeration(self):
        self.assertEqual(e7.expected_rice_random(2), 50)
        self.assertEqual(e7.corrected_rice(2,0), 100)
        self.assertEqual(e7.corrected_rice(1,1), 0)
        self.assertIsNone(e7.corrected_rice(1,0))

    def test_lopsided_boundary(self):
        votes = {'x': [(str(i), 'Yea') for i in range(20)] + [(f'n{i}', 'Nay') for i in range(5)]}
        self.assertTrue(e7.is_lopsided(votes))
        votes['x'].append(('six','Nay'))
        self.assertFalse(e7.is_lopsided(votes))


class ClassificationTests(unittest.TestCase):
    def meta(self, session, subject, bill):
        return dict(bill_info.classify_vote(subject, bill, {}), session=session)

    def test_curly_apostrophe(self):
        meta = bill_info.classify_vote('2nd reading of Bill C-222', 'C-222', {'C-222': {'type': 'Private Member’s Bill'}})
        self.assertEqual(meta['category'], 'private_members_business')

    def test_unknown_bill_not_government(self):
        self.assertEqual(self.meta('42-1','Bill , (report stage subamendment)','')['category'], 'unknown_bill')

    def test_party_and_cabinet_scope(self):
        meta = self.meta('38-1', '3rd reading of Bill C-38', 'C-38')
        self.assertEqual(bill_info.whip_status(meta,'Liberal')['scope'], 'backbench_only')
        self.assertEqual(bill_info.whip_status(meta,'Conservative')['scope'], 'whole_caucus')
        self.assertEqual(bill_info.whip_status(meta,'NDP')['status'], 'category_proxy_other')

    def test_procedural_never_inherits(self):
        meta = self.meta('38-1', 'Time allocation for Bill C-38', 'C-38')
        self.assertEqual(bill_info.whip_status(meta,'Liberal')['status'], 'category_proxy_other')

    def test_senate_and_recommittal_unresolved(self):
        for subject in ('Motion respecting Senate amendments to Bill C-14', 'Bill C-14 (recommittal to a committee)'):
            self.assertEqual(bill_info.whip_status(self.meta('42-1',subject,'C-14'),'Liberal')['status'], 'unresolved')

    def test_uncertainty_sensitivity(self):
        meta=self.meta('38-1','2nd reading of Bill C-30','C-30')
        self.assertEqual(bill_info.whip_status(meta,'Liberal')['status'],'unresolved')
        self.assertEqual(e1.eligible_category(meta,'unresolved','documented_free_excluded'),'government_bill')
        self.assertIsNone(e1.eligible_category(meta,'unresolved','uncertain_excluded'))


class IntegrityTests(unittest.TestCase):
    def make_session(self, d, yeas='1', rows=None):
        p=Path(d)/'Parliament_45-1'; p.mkdir()
        (p/'file_1.csv').write_text(HEADER + (rows if rows is not None else '1,A,Liberal,Yea,\n'),encoding='utf-8')
        (p/'votes_metadata.csv').write_text('vote_number,date,subject,bill_number,result,yeas,nays,paired\n'
                f'1,2025-06-01T15:00:00,2nd reading of Bill C-1,C-1,Agreed To,{yeas},0,0\n',encoding='utf-8')
        return p

    def test_unlisted_small_and_large_mismatch_fail(self):
        for expected in ('2','12'):
            with self.subTest(expected=expected), tempfile.TemporaryDirectory() as d:
                p=self.make_session(d,expected)
                self.assertTrue(check_data.check_session('45-1',p)[0])

    def test_empty_file_fails(self):
        with tempfile.TemporaryDirectory() as d:
            p=self.make_session(d,rows='')
            self.assertTrue(check_data.check_session('45-1',p)[0])

    def test_duplicate_metadata_fails(self):
        with tempfile.TemporaryDirectory() as d:
            p=self.make_session(d); m=p/'votes_metadata.csv'
            text=m.read_text();m.write_text(text+text.splitlines(True)[1])
            self.assertTrue(check_data.check_session('45-1',p)[0])

    def test_missing_file_and_orphan_fail(self):
        with tempfile.TemporaryDirectory() as d:
            p=self.make_session(d);(p/'file_1.csv').rename(p/'file_2.csv')
            self.assertEqual(len(check_data.check_session('45-1',p)[0]),2)

    def test_valid_fixture(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(check_data.check_session('45-1',self.make_session(d))[0],[])

    def test_real_repairs(self):
        for session, number, expected in [('42-1',871,(172,134,0)),('42-1',724,(40,245,0)),('41-1',699,(161,120,0))]:
            rows=vote_data.read_vote_rows(vote_data.ROOT/f'Parliament_{session}'/f'file_{number}.csv')
            self.assertEqual(vote_data.tally(rows),expected)
        self.assertEqual(sum(r['vote']=='Yea/Nay' for r in rows),7)


class BenchmarkTests(unittest.TestCase):
    def fixture(self):
        rows=[dict(parliament=p,party=party,rice=90,rice_contested=90,loyalty=90)
              for p,party in sorted({k[:2] for k in e7.EXPECTED})]
        benchmarks=[dict(parliament=p,party=party,metric=m,value='90',source='hand-calculated fixture')
                    for p,party,m in sorted(e7.EXPECTED)]
        return rows,benchmarks

    def test_complete_and_boundary(self):
        rows,b=self.fixture();self.assertEqual(len(e7.compare_benchmarks(rows,b)),36)
        b[0]['value']='91.00';self.assertEqual(e7.compare_benchmarks(rows,b)[0]['difference'],-1)
        b[0]['value']='91.01'
        with self.assertRaises(ValueError):e7.compare_benchmarks(rows,b)

    def test_missing_duplicate_unexpected_invalid(self):
        for kind in ('missing','duplicate','unexpected','nan','inf','out_of_range','empty','missing_observed'):
            rows,b=self.fixture()
            if kind=='missing':b.pop()
            elif kind=='duplicate':b.append(b[0])
            elif kind=='unexpected':b[0]['parliament']=99
            elif kind=='nan':b[0]['value']='NaN'
            elif kind=='inf':b[0]['value']='Infinity'
            elif kind=='out_of_range':b[0]['value']='101'
            elif kind=='empty':b[0]['value']=''
            elif kind=='missing_observed':rows.pop()
            with self.subTest(kind=kind),self.assertRaises(ValueError):e7.compare_benchmarks(rows,b)


class OutputProtectionTests(unittest.TestCase):
    def test_preflight_stops_both_experiments_before_writing(self):
        with tempfile.TemporaryDirectory() as d:
            output=Path(d)/'results';output.mkdir()
            sentinel=output/'summary.csv';sentinel.write_text('previous results')
            for module, target in [(e1,'experiments.experiment_e1.require_valid_corpus'),(e7,'check_data.require_valid_corpus')]:
                with patch(target,side_effect=check_data.IntegrityError('empty unapproved division')):
                    with self.assertRaises(check_data.IntegrityError):module.main(output)
                self.assertEqual(sentinel.read_text(),'previous results')
                self.assertEqual([p.name for p in output.iterdir()],['summary.csv'])

    def test_failed_benchmark_does_not_write_outputs(self):
        with tempfile.TemporaryDirectory() as d, patch('check_data.require_valid_corpus'), patch.object(e7,'parliament_sessions',return_value={}), patch.object(e7,'load_benchmarks',return_value=[]):
            output=Path(d)/'results'
            with self.assertRaises(ValueError):e7.main(output)
            self.assertFalse(output.exists())


class SourceArchiveTests(unittest.TestCase):
    def test_pdf_archive_interstitial_is_rejected(self):
        from tools.fetch_audit_evidence import validate_content
        with self.assertRaises(ValueError):
            validate_content('source.pdf', b'<html>Continue to publication</html>')
        validate_content('source.pdf', b'%PDF-1.7\n')

    def test_html_cannot_masquerade_as_vote_xml(self):
        from tools.fetch_audit_evidence import validate_content
        with self.assertRaises(ValueError):
            validate_content('votes.xml', b'<html><body>Error</body></html>')


if __name__ == '__main__':
    unittest.main()

"""Hand-worked denominator checks and repair/serialization contracts."""
import gzip
import csv
import json
from pathlib import Path
import tempfile
import unittest

from experiments.design_checks import summarize
from tools.export_dataset import member_record
from provenance import digest
from experiment_io import write_csv, write_json
from tools.verify_dataset import verify


def observation(session='38-1', bill='C-1', dissenters=1, **changes):
    return dict(session=session, bill=bill, dissenters=dissenters, governing=True,
                majority_defined=True, whip_status='category_proxy_other',
                category='government_bill', binary_members=4, **changes)


class DesignChecks(unittest.TestCase):
    def test_repeated_bill_and_session_keys(self):
        rows = [observation(), observation(dissenters=0), observation(dissenters=0),
                observation(session='39-1', dissenters=0)]
        units, weights, sizes = summarize(rows)
        self.assertEqual(len(units), 2)
        self.assertEqual(weights[0]['all_division_rate'], 25)
        self.assertEqual(weights[0]['equal_bill_mean_rate'], 16.666667)
        self.assertEqual(sizes[0]['minority_member_vote_rate'], 6.25)

    def test_unnumbered_and_undefined_are_not_zero(self):
        _, weights, sizes = summarize([observation(bill='')])
        self.assertEqual(weights[0]['unnumbered_divisions'], 1)
        self.assertEqual(weights[0]['all_division_rate'], 100)
        self.assertIsNone(weights[0]['equal_bill_mean_rate'])
        self.assertIsNone(sizes[2]['division_dissent_rate'])

    def test_scope_exclusions_and_size_boundaries(self):
        rows = [observation() for _ in range(7)]
        rows[0]['whip_status'] = 'documented_free'
        rows[1].update(majority_defined=False, dissenters='')
        rows[2]['governing'] = False
        for row, size in zip(rows[3:], [100, 101, 150, 151]):
            row['binary_members'] = size
        _, weights, sizes = summarize(rows)
        self.assertEqual(weights[0]['eligible_divisions'], 4)
        self.assertEqual([r['divisions'] for r in sizes[:4]], [4, 1, 2, 1])


class ExportChecks(unittest.TestCase):
    def test_round_trip_rejects_wrong_analysis_denominator_and_changed_content(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            write_csv(root/'divisions.csv', [dict(session='38-1', division=1, yeas=3, nays=1, paired=0)])
            rows = [member_record('38-1', 1, dict(member_id=str(i), member=f'M{i}',
                    party='Liberal', vote='Yea' if i < 4 else 'Nay', paired=False), {}) for i in range(1, 5)]
            with gzip.open(root/'members.csv.gz', 'wt', encoding='utf-8', newline='') as handle:
                writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator='\n')
                writer.writeheader()
                writer.writerows(rows)
            write_json(root/'manifest.json', dict(files={p.name: digest(p) for p in root.iterdir()},
                sessions={'38-1': dict(divisions=1, member_observations=4)}))
            audit = [dict(session='38-1', division=1, party=p, majority_defined=p == 'Liberal',
                     binary_members=4 if p == 'Liberal' else 0, dissenters=1 if p == 'Liberal' else '')
                     for p in ('Conservative', 'Liberal', 'NDP', 'Bloc Québécois', 'Green Party')]
            write_csv(root/'classification.csv', audit)
            verify(root, root/'classification.csv')
            audit[1]['binary_members'] = 3
            write_csv(root/'classification.csv', audit)
            with self.assertRaisesRegex(ValueError, 'denominator mismatch'):
                verify(root, root/'classification.csv')
            (root/'members.csv.gz').write_bytes(gzip.compress(b'changed\n', mtime=0))
            with self.assertRaisesRegex(ValueError, 'hash mismatch'):
                verify(root, root/'classification.csv')

    def test_flags_and_repair_provenance(self):
        row = dict(member_id='1', member='A', party='Québec debout', vote='Yea/Nay', paired=False)
        r = member_record('42-1', 1, row, {'dual_member_ids': ['1']})
        self.assertEqual((r['yea'], r['nay'], r['binary_vote']), (1, 1, ''))
        self.assertEqual((r['repair_id'], r['party_analytic']), ('42-1/1', 'Independent'))
        row.update(vote='Yea', paired=True)
        r = member_record('42-1', 1, row, {})
        self.assertEqual((r['yea'], r['paired'], r['binary_vote'], r['repair_id']), (1, 1, '', ''))
        self.assertEqual(member_record('42-1', 1, row, {'replacement': 'x'})['repair_id'], '42-1/1')
        self.assertEqual(member_record('42-1', 1, row, {'append_rows': [row]})['repair_id'], '42-1/1')

    def test_compression_metadata_does_not_change_content_hash(self):
        with tempfile.TemporaryDirectory() as name:
            a, b = Path(name)/'a.gz', Path(name)/'b.gz'
            a.write_bytes(gzip.compress(b'a,b\n1,2\n', mtime=0))
            b.write_bytes(gzip.compress(b'a,b\n1,2\n', mtime=100))
            self.assertEqual(digest(a), digest(b))
            self.assertNotEqual(digest(a, binary=True), digest(b, binary=True))


if __name__ == '__main__':
    unittest.main()

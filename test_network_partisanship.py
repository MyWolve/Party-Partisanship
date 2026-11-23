"""Run as: python -m unittest test_network_partisanship.py -v
Place alongside network_partisanship.py in the Party-Partisanship repository.
"""
import unittest
import numpy as np

from network_partisanship import cell_metrics, layout_graph, pair_mask, similarity


class NetworkPartisanshipTests(unittest.TestCase):
    def test_agreement_ignores_absences(self):
        x = np.array([[1, 1, 0, -1], [1, -1, 1, -1], [-1, 0, 1, 0]], dtype=np.float32)
        r, count, shared = similarity(x)
        self.assertEqual(shared[0, 1], 3)
        self.assertEqual(count[0, 1], 2)
        self.assertAlmostEqual(r[0, 1], 2 / 3)
        self.assertEqual(shared[0, 2], 1)
        self.assertEqual(count[0, 2], 0)
        self.assertTrue(np.isnan(r[0, 0]))

    def test_party_pairs_exclude_independents(self):
        p = ['Liberal', 'Liberal', 'Conservative', 'Independent']
        co = np.full((4, 4), 25)
        valid, sp, cp = pair_mask(p, co, 20)
        self.assertEqual(int(valid.sum()), 3)
        self.assertEqual(int(sp.sum()), 1)
        self.assertEqual(int(cp.sum()), 2)

    def test_complete_party_separation(self):
        x = np.array([[1]*20, [1]*20, [-1]*20, [-1]*20], dtype=np.float32)
        party = ['Liberal', 'Liberal', 'Conservative', 'Conservative']
        m, pairs, _, agree, edges = cell_metrics('fixture', x, party, 20, .8, 0)
        self.assertEqual(m.status, 'ok')
        self.assertAlmostEqual(m.mean_same, 1)
        self.assertAlmostEqual(m.mean_cross, 0)
        self.assertEqual(m.same_party_pairs, 2)
        self.assertEqual(m.cross_party_pairs, 4)
        self.assertEqual(m.graph_cross_edges, 0)
        xy, shown = layout_graph(agree, edges, party)
        self.assertEqual(xy.shape, (4, 2))
        self.assertEqual(shown.shape[1], 2)

    def test_identical_cross_party_voting(self):
        x = np.array([[1]*30, [1]*30, [1]*30, [1]*30], dtype=np.float32)
        party = ['Liberal', 'Liberal', 'Conservative', 'Conservative']
        m, _, _, _, _ = cell_metrics('fixture', x, party, 20, .8, 0)
        self.assertAlmostEqual(m.gap, 0)
        self.assertEqual(m.graph_cross_edges, 4)
        self.assertEqual(m.cross_edge_share, 1)

    def test_one_vote_not_supported(self):
        x = np.array([[1], [-1]], dtype=np.float32)
        m, _, _, _, _ = cell_metrics('fixture', x,
                                     ['Liberal', 'Conservative'], 20, .8, 0)
        self.assertEqual(m.status, 'insufficient_data')


if __name__ == '__main__':
    unittest.main()
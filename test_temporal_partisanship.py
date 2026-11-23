"""Temporal vote-network tests: python -m unittest test_temporal_partisanship.py -v."""
import unittest
import numpy as np
from temporal_partisanship import (
    Corpus, Window, quarter_windows, cumulative_windows, rolling_windows,
    window_parties, evaluate, adjacency_correspondence, party_profiles,
    profile_change, align_common_id_positions,
)

class TemporalNetworkTests(unittest.TestCase):
    def corpus(self):
        rng = np.random.default_rng(12)
        base = rng.choice([-1, 1], size=(6, 25)).astype(np.float32)
        v = np.tile(base, (1, 4))
        p = np.array([0, 0, 0, 1, 1, 1], dtype=np.int8)
        return Corpus('fixture', [f'mp-{i}' for i in range(6)], {}, v,
                      np.tile(p[:, None], (1,100)), list(range(1,101)),
                      ['2000-01-01']*100, ['government_bill']*100, ['']*100)

    def test_quarters(self):
        self.assertEqual([(w.start,w.end) for w in quarter_windows(13)],
                         [(0,3),(3,6),(6,9),(9,13)])
        self.assertEqual(cumulative_windows(13)[-1].end,13)
        self.assertTrue(all(w.start==0 for w in cumulative_windows(13)))

    def test_rolling_covers_endpoint(self):
        self.assertEqual([(w.start,w.end) for w in rolling_windows(11,5,4)],
                         [(0,5),(4,9),(6,11)])
        self.assertEqual(rolling_windows(1,100,25)[0].end,1)
        with self.assertRaises(ValueError):
            rolling_windows(100,25,0)

    def test_parties_are_assigned_inside_window(self):
        c=self.corpus()
        c.affiliations[0,25:50] = 1
        self.assertEqual(window_parties(c.affiliations[:,0:25])[0][0], 'Liberal')
        self.assertEqual(window_parties(c.affiliations[:,25:50])[0][0], 'Conservative')
        self.assertEqual(window_parties(c.affiliations[:,0:50])[1],1)

    def test_correspondence_identical_quarters(self):
        c=self.corpus()
        q=quarter_windows(100)
        a=evaluate(c,q[0],min_common=10,min_window_divisions=10,threshold=.5)
        b=evaluate(c,q[1],min_common=10,min_window_divisions=10,threshold=.5)
        m=adjacency_correspondence(a,b,10)
        self.assertEqual(m['comparable_pairs'],15)
        self.assertAlmostEqual(m['agreement_correlation'],1)
        self.assertAlmostEqual(m['edge_jaccard'],1)
        self.assertEqual(m['edges_gained'],0)

    def test_insufficient_window(self):
        c=self.corpus()
        r=evaluate(c,Window('independent','Q1',0,25,1),
                   min_common=10,min_window_divisions=40)
        self.assertEqual(r.metric.status,'insufficient_window')
        self.assertEqual(r.pair_summary,{})

    def test_mp_party_affinity_stable_across_identical_votes(self):
        c=self.corpus()
        q=quarter_windows(100)
        a=evaluate(c,q[0],min_common=10,min_window_divisions=10)
        b=evaluate(c,q[1],min_common=10,min_window_divisions=10)
        changes=profile_change(party_profiles(a,10),party_profiles(b,10))
        self.assertEqual(len(changes),6)
        self.assertTrue(all(x['rms_party_affinity_change']<1e-9 for x in changes))

    def test_layout_alignment(self):
        c=self.corpus()
        a=evaluate(c,quarter_windows(100)[0],min_common=10,min_window_divisions=10)
        b=evaluate(c,quarter_windows(100)[1],min_common=10,min_window_divisions=10)
        xy=np.array([[0,0],[1,0],[0,1],[1,1],[2,0],[0,2]],dtype=float)
        a.xy=xy.copy()
        b.xy=xy@np.array([[0,-1],[1,0]])+np.array([4,7])
        align_common_id_positions(a,b)
        np.testing.assert_allclose(a.xy,b.xy,atol=1e-10)

if __name__ == '__main__':
    unittest.main()

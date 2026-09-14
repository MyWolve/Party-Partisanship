"""Hand-worked sequence boundaries for generated E1 narrative."""
import unittest
from experiments.e1_narrative import longest_clean_run


def row(n, session='39-1', **changes):
    r = dict(session=session, division=n, governing=True, party='Conservative',
             category='government_bill', majority_defined=True, whip_status='category_proxy_other', dissenters=0)
    r.update(changes)
    return r


class NarrativeTests(unittest.TestCase):
    def test_dissent_resets_and_sessions_continue(self):
        rs = [row(1), row(2, dissenters=1), row(3), row(1, '39-2')]
        self.assertEqual(longest_clean_run(rs, ['39-1', '39-2']), rs[2:])

    def test_order_is_numeric(self):
        rs = [row(10), row(9, dissenters=1), row(11)]
        self.assertEqual([r['division'] for r in longest_clean_run(rs, ['39-1'])], [10, 11])

    def test_governing_party_transition_breaks_run(self):
        rs = [row(1), row(2), row(1, '42-1', party='Liberal'), row(2, '42-1', party='Liberal')]
        self.assertEqual(longest_clean_run(rs, ['39-1', '42-1']), rs[:2])

    def test_ineligible_observations_neither_extend_nor_break(self):
        rs = [row(1), row(2, whip_status='documented_free', dissenters=1),
              row(3, governing=False, dissenters=1), row(4, majority_defined=False, dissenters=''),
              row(5, category='private_members_business', dissenters=1), row(6)]
        self.assertEqual([r['division'] for r in longest_clean_run(rs, ['39-1'])], [1, 6])

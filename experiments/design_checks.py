"""Descriptive E1 checks for repeated bills and observed party participation."""
from collections import defaultdict

CATEGORIES = ('government_bill', 'private_members_business')


def percent(n, d):
    return round(100 * n / d, 6) if d else None


def summarize(rows):
    # Use the same population as the main E1 result. A missing majority is
    # undefined, and documented free stages are excluded before weighting.
    eligible = [r for r in rows if r['governing'] and r['majority_defined']
                and r['whip_status'] != 'documented_free' and r['category'] in CATEGORIES]
    bills = defaultdict(list)
    for r in eligible:
        if r['bill']:
            bills[r['session'], r['category'], r['bill']].append(r)
    units = [dict(session=s, category=c, bill=b, divisions=len(rs),
                  with_dissent=sum(r['dissenters'] > 0 for r in rs),
                  dissent_rate=percent(sum(r['dissenters'] > 0 for r in rs), len(rs)))
             for (s, c, b), rs in sorted(bills.items())]
    weighting, participation = [], []
    for category in CATEGORIES:
        selected = [r for r in eligible if r['category'] == category]
        numbered = [r for r in selected if r['bill']]
        groups = [rs for (s, c, b), rs in bills.items() if c == category]
        weighting.append(dict(category=category, eligible_divisions=len(selected),
            unnumbered_divisions=len(selected)-len(numbered), numbered_divisions=len(numbered),
            session_bill_units=len(groups),
            all_division_rate=percent(sum(r['dissenters'] > 0 for r in selected), len(selected)),
            numbered_division_rate=percent(sum(r['dissenters'] > 0 for r in numbered), len(numbered)),
            equal_bill_mean_rate=(round(sum(sum(r['dissenters'] > 0 for r in rs)/len(rs)
                                          for rs in groups)/len(groups)*100, 6) if groups else None)))
        for label, lo, hi in [('all', 1, float('inf')), ('1-100', 1, 100),
                              ('101-150', 101, 150), ('151+', 151, float('inf'))]:
            rs = [r for r in selected if lo <= r['binary_members'] <= hi]
            members = sum(r['binary_members'] for r in rs)
            dissenters = sum(r['dissenters'] for r in rs)
            participation.append(dict(category=category, observed_party_voters=label,
                divisions=len(rs), with_dissent=sum(r['dissenters'] > 0 for r in rs),
                division_dissent_rate=percent(sum(r['dissenters'] > 0 for r in rs), len(rs)),
                binary_member_votes=members, minority_member_votes=dissenters,
                minority_member_vote_rate=percent(dissenters, members)))
    return units, weighting, participation

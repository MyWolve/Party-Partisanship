"""Build benchmarks_e7.csv from Godbout & Høyland's raw voting data.

The Dataverse deposit (Canadian Parliament Voting Data, 1867-2015)
contains raw member-by-division matrices, not precomputed unity scores,
so the benchmark values are COMPUTED from their data using the exact
metric functions and filter constants imported from experiment_e7.py.
Definitions therefore cannot diverge between the two sides of the
comparison; any residual difference measures data collection, not
metric arithmetic.

Vote coding (deposit readme): 1=yes, 2=no, 3=paired, 4-7=recording
combinations, 8=abstain (Senate only), 9=not-vote, 99=not sitting,
9999=error. Only 1 and 2 enter the metrics, mirroring our pipeline's
Yea/Nay-only observability. Combos 4-7 (a handful per parliament) are
excluded and counted.

Party rows: members who switch affiliation appear as separate rows
(distinct Id.2), each carrying the party held during that term --
matching our affiliation-at-time-of-vote loyalty keying.
"""

import csv
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(HERE)
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, HERE)

from experiment_e7 import (LOPSIDED_MINORITY, MIN_VOTES_PER_MP, TRACKED,
                           corrected_rice, is_lopsided)
from visualize_parliament import count_yea_nay, party_majority_side

DATA_DIR = os.path.join(HERE, "experiment_7_data")
OUT = os.path.join(HERE, "benchmarks_e7.csv")

SOURCE = ("Godbout & Hoyland 2017, Canadian Parliament Voting Data "
          "1867-2015, Harvard Dataverse, {fname}; computed with E7 "
          "definitions (lopsided<={lop}, min {mv} votes/MP)")

PARTY_MAP = {
    "Liberal Party of Canada": "Liberal",
    "Conservative Party of Canada": "Conservative",
    "New Democratic Party": "NDP",
    "Bloc Quebecois": "Bloc Québécois",
    "Green Party of Canada": "Green Party",
}
VOTE_MAP = {"1": "Yea", "2": "Nay"}


def load_house(path):
    """Yield one votes dict {party: [(member, votestr), ...]} per division."""
    with open(path, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f, delimiter="\t"))
    members = [r for r in rows if r.get("vote.id") != "Date"]
    votecols = [c for c in rows[0] if c and c.startswith("H")]
    skipped = 0
    divisions = []
    for col in votecols:
        votes = {}
        for i, r in enumerate(members):
            raw = (r.get(col) or "").strip()
            if raw in ("3", "4", "5", "6", "7", "8"):
                skipped += raw in ("4", "5", "6", "7")
                continue
            vote = VOTE_MAP.get(raw)
            if vote is None:
                continue
            party = PARTY_MAP.get(r.get("Party.Name", "").strip(),
                                  "Independent")
            member = r.get("Id.2") or f"row{i}:{r.get('Name', '')}"
            votes.setdefault(party, []).append((member, vote))
        divisions.append(votes)
    return divisions, skipped


def unity_from_divisions(divisions):
    """Mirror of experiment_e7.parliament_unity's accumulation loop, fed
    prebuilt votes dicts; all metric arithmetic uses imported functions."""
    sums = {p: {"rice": [0.0, 0], "rice_contested": [0.0, 0]}
            for p in TRACKED}
    mp = {}
    n_contested = 0
    for votes in divisions:
        lopsided = is_lopsided(votes)
        if not lopsided:
            n_contested += 1
        for party in TRACKED:
            if party not in votes:
                continue
            yea, nay = count_yea_nay(votes[party])
            if yea + nay == 0:
                continue
            rice = abs(yea - nay) / (yea + nay) * 100
            sums[party]["rice"][0] += rice
            sums[party]["rice"][1] += 1
            if lopsided:
                continue
            sums[party]["rice_contested"][0] += rice
            sums[party]["rice_contested"][1] += 1
            majority = party_majority_side(votes[party])
            if majority is None:
                continue
            for member, vote in votes[party]:
                record = mp.setdefault((member, party), [0, 0])
                record[1] += 1
                if vote == majority:
                    record[0] += 1
    result = {}
    for party in TRACKED:
        entry = {m: (round(t / c, 2) if c else None)
                 for m, (t, c) in sums[party].items()}
        loyalties = [a / t * 100 for (_, p), (a, t) in mp.items()
                     if p == party and t >= MIN_VOTES_PER_MP]
        entry["loyalty"] = (round(sum(loyalties) / len(loyalties), 2)
                            if loyalties else None)
        entry["n_mps"] = len(loyalties)
        result[party] = entry
    return result, n_contested


def main():
    out_rows = []
    for parl in (38, 39, 40):
        fname = f"House-{parl}.tab"
        divisions, skipped = load_house(os.path.join(DATA_DIR, fname))
        unity, n_contested = unity_from_divisions(divisions)
        print(f"House-{parl}: {len(divisions)} divisions "
              f"({n_contested} contested), {skipped} combo-coded "
              f"member-votes excluded")
        for party, entry in unity.items():
            for metric in ("rice", "rice_contested", "loyalty"):
                if entry[metric] is None:
                    continue
                out_rows.append({
                    "parliament": parl, "party": party, "metric": metric,
                    "value": entry[metric],
                    "source": SOURCE.format(fname=fname,
                                            lop=LOPSIDED_MINORITY,
                                            mv=MIN_VOTES_PER_MP)})
            print(f"  {party:16} rice {entry['rice']}, contested "
                  f"{entry['rice_contested']}, loyalty {entry['loyalty']} "
                  f"({entry['n_mps']} MPs)")
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["parliament", "party", "metric",
                                          "value", "source"])
        w.writeheader()
        w.writerows(out_rows)
    print(f"\nWrote {len(out_rows)} benchmark rows to {OUT}")


if __name__ == "__main__":
    main()
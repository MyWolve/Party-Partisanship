"""Experiment 7: Validation and robustness.

Before the whip-test findings travel anywhere, certify the pipeline:

  1. Compute party unity per PARLIAMENT (pooling sessions) in forms
     comparable to the published literature. Godbout & Høyland's filters
     are mirrored exactly as documented: lop-sided divisions excluded
     (all but <= 5 MPs on one side) and MPs with fewer than 25 recorded
     votes dropped from loyalty averages.
  2. Compare against published benchmarks where available. Fill
     experiments/benchmarks_e7.csv (parliament, party, metric, value,
     source) from Lost on Division's figures or the BJPS replication
     data (dataverse.harvard.edu, Godbout & Høyland 2017); the script
     prints a side-by-side comparison for any rows present.
  3. Robustness: recompute unity under a Desposato-style small-group
     correction (share of possible cohesion above the random-voting
     baseline for a group of that size) and under MP-weighted vs
     vote-weighted averaging. Conclusions that survive all variants are
     robust to the known biases of the raw Rice Index.

Note on the Agreement Index (Hix-Noury-Roland): NOT implemented. The
House's per-division files record only voters and paired members, so
abstention/absence is unobservable; with two observable options the
Agreement Index reduces to a transform of Rice and adds no information.

Outputs (results_e7/): unity_by_parliament.csv, robustness figure,
console comparison against any provided benchmarks.
"""

import csv
import math
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

# You might get an error importing visualize_parliament, but the above direct setting of the 
# directory should resolve this when you actually execute the file. 
from visualize_parliament import (PARTIES, PARTY_COLORS, count_yea_nay,
                                  load_parliament, party_majority_side)

RESULTS_DIR = os.path.join(PROJECT_ROOT, "results_e7")
BENCHMARKS = os.path.join(PROJECT_ROOT, "experiments", "benchmarks_e7.csv")

# Godbout & Høyland's documented filters.
LOPSIDED_MINORITY = 5    # lop-sided: all but <= 5 MPs vote the same way
MIN_VOTES_PER_MP = 25    # MPs below this are dropped from loyalty averages

TRACKED = [p for p in PARTIES if p != "Independent"]


def parliament_sessions():
    """Group Parliament_<P>-<S> directories by parliament number."""
    groups = {}
    for name in sorted(os.listdir(PROJECT_ROOT)):
        path = os.path.join(PROJECT_ROOT, name)
        if name.startswith("Parliament_") and os.path.isdir(path):
            parliament = name.replace("Parliament_", "").split("-")[0]
            groups.setdefault(int(parliament), []).append(path)
    return groups


def expected_rice_random(n, _cache={}):
    """E[Rice] for n members voting independently 50/50 — the small-group
    inflation baseline (cf. Desposato 2005). Exact, via the binomial pmf."""
    if n not in _cache:
        total = sum(math.comb(n, k) * abs(2 * k - n) for k in range(n + 1))
        _cache[n] = total / (2 ** n * n) * 100
    return _cache[n]


def corrected_rice(yea, nay):
    """Desposato-style correction: share of possible cohesion above the
    random-voting baseline for a group of this size, scaled 0-100."""
    n = yea + nay
    rice = abs(yea - nay) / n * 100
    baseline = expected_rice_random(n)
    if baseline >= 100:
        return None
    return max(0.0, (rice - baseline) / (100 - baseline) * 100)


def is_lopsided(votes):
    """All but <= LOPSIDED_MINORITY MPs in the whole House on one side."""
    yea = nay = 0
    for party in votes:
        y, n = count_yea_nay(votes[party])
        yea += y
        nay += n
    return min(yea, nay) <= LOPSIDED_MINORITY


def parliament_unity(directories):
    """Unity statistics for one parliament (sessions pooled).

    Returns {party: {metric: value}} with metrics:
      rice            vote-weighted mean Rice, all divisions
      rice_contested  same, lop-sided divisions excluded
      rice_corrected  small-group-corrected Rice, lop-sided excluded
      loyalty         MP-weighted: mean share of votes with party majority
                      (>= MIN_VOTES_PER_MP), lop-sided excluded
      divisions       divisions used for the contested metrics
    """
    sums = {p: {"rice": [0.0, 0], "rice_contested": [0.0, 0],
                "rice_corrected": [0.0, 0]} for p in TRACKED}
    mp = {}  # (member, party) -> [aligned, total]
    divisions_contested = 0

    for directory in directories:
        for _, votes in load_parliament(directory):
            lopsided = is_lopsided(votes)
            if not lopsided:
                divisions_contested += 1
            for party in TRACKED:
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
                corrected = corrected_rice(yea, nay)
                if corrected is not None:
                    sums[party]["rice_corrected"][0] += corrected
                    sums[party]["rice_corrected"][1] += 1
                majority = party_majority_side(votes[party])
                if majority is None:
                    continue
                for member, vote in votes[party]:
                    if vote in ("Yea", "Nay"):
                        record = mp.setdefault((member, party), [0, 0])
                        record[1] += 1
                        if vote == majority:
                            record[0] += 1

    result = {}
    for party in TRACKED:
        entry = {}
        for metric, (total, count) in sums[party].items():
            entry[metric] = round(total / count, 2) if count else None
        loyalties = [aligned / total * 100
                     for (member, p), (aligned, total) in mp.items()
                     if p == party and total >= MIN_VOTES_PER_MP]
        entry["loyalty"] = (round(sum(loyalties) / len(loyalties), 2)
                            if loyalties else None)
        entry["mps"] = len(loyalties)
        entry["divisions"] = divisions_contested
        result[party] = entry
    return result


def load_benchmarks():
    if not os.path.exists(BENCHMARKS):
        return []
    with open(BENCHMARKS, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def main():
    os.makedirs(RESULTS_DIR, exist_ok=True)
    groups = parliament_sessions()

    rows = []
    for parliament, directories in sorted(groups.items()):
        unity = parliament_unity(directories)
        for party, entry in unity.items():
            if entry["rice"] is None:
                continue
            rows.append({"parliament": parliament, "party": party, **entry})

    out = os.path.join(RESULTS_DIR, "unity_by_parliament.csv")
    with open(out, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "parliament", "party", "rice", "rice_contested",
            "rice_corrected", "loyalty", "mps", "divisions"])
        writer.writeheader()
        writer.writerows(rows)

    print("E7: unity by parliament (lop-sided excluded where marked)")
    print("=" * 78)
    print(f"{'parl':5}{'party':17}{'rice':>7}{'contested':>11}"
          f"{'corrected':>11}{'loyalty':>9}{'MPs':>5}")
    for r in rows:
        print(f"{r['parliament']:<5}{r['party']:17}"
              f"{r['rice']:>7}{str(r['rice_contested']):>11}"
              f"{str(r['rice_corrected']):>11}{str(r['loyalty']):>9}"
              f"{r['mps']:>5}")

    benchmarks = load_benchmarks()
    if benchmarks:
        print("\nBenchmark comparison (published values from "
              "benchmarks_e7.csv):")
        ours = {(r["parliament"], r["party"]): r for r in rows}
        for b in benchmarks:
            key = (int(b["parliament"]), b["party"])
            metric = b.get("metric", "loyalty")
            our_value = ours.get(key, {}).get(metric)
            published = float(b["value"])
            if our_value is None:
                print(f"  P{b['parliament']} {b['party']} {metric}: "
                      f"published {published}, ours: n/a")
                continue
            print(f"  P{b['parliament']} {b['party']} {metric}: "
                  f"published {published}, ours {our_value} "
                  f"(diff {our_value - published:+.2f}) [{b['source']}]")
    else:
        print("\nNo benchmarks_e7.csv found. To compare against published "
              "figures, create experiments/benchmarks_e7.csv with columns "
              "parliament,party,metric,value,source (metric: rice, "
              "rice_contested, or loyalty). Godbout & Høyland 2017's "
              "replication data: dataverse.harvard.edu (BJPolS dataverse).")

    # Robustness figure: raw vs corrected Rice per party, by parliament
    parliaments = sorted({r["parliament"] for r in rows})
    plt.figure(figsize=(14, 7))
    for party in TRACKED:
        series = {r["parliament"]: r for r in rows if r["party"] == party}
        xs = [p for p in parliaments if p in series
              and series[p]["rice_contested"] is not None]
        if not xs:
            continue
        plt.plot(xs, [series[p]["rice_contested"] for p in xs],
                 color=PARTY_COLORS[party], marker="o", label=party)
        cx = [p for p in xs if series[p]["rice_corrected"] is not None]
        plt.plot(cx, [series[p]["rice_corrected"] for p in cx],
                 color=PARTY_COLORS[party], marker="x", linestyle="--",
                 alpha=0.6)
    plt.xlabel("Parliament")
    plt.ylabel("Mean Rice (contested divisions)")
    plt.title("Unity by parliament: raw (solid) vs small-group-corrected "
              "(dashed) Rice")
    plt.xticks(parliaments)
    plt.legend()
    plt.grid(True, linestyle="--", alpha=0.4)
    plt.tight_layout()
    plt.savefig(os.path.join(RESULTS_DIR, "unity_robustness.png"))
    plt.close()

    print(f"\nWrote {out} and unity_robustness.png to {RESULTS_DIR}/")


if __name__ == "__main__":
    main()
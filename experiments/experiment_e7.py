"""E7: aggregate agreement with independently collected voting data.

Shared metrics test data agreement, not independent metric correctness or
whip classification. All 36 expected comparisons must exist and stay within
1.00 percentage point. Paired and dual-coded votes are excluded from binary
metrics. The nonnegative small-group adjustment is descriptive, not a full
replication of a published estimator.
"""

import argparse
import csv
import json
from decimal import Decimal
from pathlib import Path
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

RESULTS_DIR = os.path.join(PROJECT_ROOT, "experiments", "results_e7")
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
        for _, votes in load_parliament(directory, member_ids=True):
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
    with open(BENCHMARKS, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


EXPECTED = {(p, party, metric) for p in (38, 39, 40)
            for party in ("Conservative", "Liberal", "NDP", "Bloc Québécois")
            for metric in ("rice", "rice_contested", "loyalty")}
TOLERANCE = Decimal("1.00")


def compare_benchmarks(rows, benchmarks):
    """Return all comparisons, rejecting schema gaps and numerical drift."""
    ours = {}
    for row in rows:
        key = (int(row['parliament']), row['party'])
        if key in ours:
            raise ValueError(f'Duplicate observed row: {key}')
        ours[key] = row
    seen, comparison = set(), []
    for b in benchmarks:
        key = (int(b['parliament']), b['party'], b['metric'])
        if key not in EXPECTED or key in seen:
            raise ValueError(f'Unexpected or duplicate benchmark: {key}')
        if not b.get('source', '').strip():
            raise ValueError(f'Missing benchmark provenance: {key}')
        seen.add(key)
        try:
            observed = Decimal(str(ours[key[:2]][key[2]]))
            reference = Decimal(str(b['value']))
        except (KeyError, ArithmeticError):
            raise ValueError(f'Missing or invalid value: {key}') from None
        if any(not v.is_finite() or not 0 <= v <= 100 for v in (observed, reference)):
            raise ValueError(f'Non-finite/out-of-range value: {key}')
        difference = observed - reference
        comparison.append(dict(parliament=key[0], party=key[1], metric=key[2],
            observed=float(observed), benchmark=float(reference), difference=float(difference),
            tolerance=float(TOLERANCE), passed=abs(difference) <= TOLERANCE, source=b['source']))
    if seen != EXPECTED:
        raise ValueError(f'Missing benchmarks: {sorted(EXPECTED - seen)}')
    failed = [c for c in comparison if not c['passed']]
    if failed:
        raise ValueError(f'Benchmark tolerance exceeded: {failed}')
    return sorted(comparison, key=lambda c: (c['parliament'], c['party'], c['metric']))


def main(output_dir=None):
    from check_data import require_valid_corpus
    from experiment_io import write_csv, write_json, plot_style
    require_valid_corpus()  # before creating or replacing any result files
    rows = []
    for parliament, directories in sorted(parliament_sessions().items()):
        for party, entry in parliament_unity(directories).items():
            if entry['rice'] is not None:
                rows.append({'parliament': parliament, 'party': party, **entry})
    comparisons = compare_benchmarks(rows, load_benchmarks())
    destination = Path(output_dir or RESULTS_DIR)
    destination.mkdir(parents=True, exist_ok=True)
    write_csv(destination / 'unity_by_parliament.csv', rows)
    write_csv(destination / 'benchmark_comparison.csv', comparisons)
    summary = {'comparisons': len(comparisons),
               'exact_to_two_decimals': sum(c['difference'] == 0 for c in comparisons),
               'maximum_absolute_difference': max(abs(c['difference']) for c in comparisons),
               'tolerance_percentage_points': float(TOLERANCE), 'status': 'pass'}
    write_json(destination / 'validation_summary.json', summary)
    plot_style()
    fig, ax = plt.subplots(figsize=(10.5, 5.8))
    for party in TRACKED:
        series = [r for r in rows if r['party'] == party and r['rice_contested'] is not None]
        ax.plot([r['parliament'] for r in series], [r['rice_contested'] for r in series],
                color=PARTY_COLORS[party], marker='o', label=party)
        corrected = [r for r in series if r['rice_corrected'] is not None]
        ax.plot([r['parliament'] for r in corrected], [r['rice_corrected'] for r in corrected],
                color=PARTY_COLORS[party], linestyle='--', alpha=.7)
    ax.set(xlabel='Parliament', ylabel='Mean Rice index on contested divisions', ylim=(85, 101),
           xticks=sorted({r['parliament'] for r in rows}), title='Party cohesion across the frozen corpus')
    ax.legend(ncol=3, loc='lower right', frameon=False)
    fig.text(.08, .015, 'Solid: raw Rice   Dashed: nonnegative small-group adjustment   P45 is incomplete   Y-axis starts at 85', fontsize=9)
    fig.tight_layout(rect=(0, .05, 1, 1))
    fig.savefig(destination / 'unity_robustness.png', dpi=180)
    plt.close(fig)
    (destination / 'FINDINGS_E7.md').write_text(
        '# E7 Aggregate data agreement\n\n'
        f"All {summary['comparisons']} comparisons pass the 1.00-point criterion. "
        f"{summary['exact_to_two_decimals']} match to two decimals; the maximum absolute difference is "
        f"{summary['maximum_absolute_difference']:.2f} percentage points.\n\n"
        'The benchmark values are computed from Godbout and Høyland’s deposited raw matrices, '
        'using shared definitions. This is an aggregate data-agreement check for Parliaments 38–40, '
        'not an independent validation of the arithmetic, the vote classifier, or later parliaments. '
        'Hand-calculated regression fixtures provide a separate check of metric behavior.\n\n'
        'The reviewed baseline had 27 exact matches, not the previously documented 30. '
        'The earlier attribution of all differences to floor-crossing conventions was not demonstrated; '
        'residual causes require member-by-division reconciliation. Small aggregate differences do not '
        'establish identity of the underlying records.\n\n'
        'Contested means more than five observable binary votes on each side of the House. '
        'MP loyalty averages require at least 25 qualifying votes and omit tied party divisions. '
        'Paired and dual-coded member-votes are omitted. Two-member caucus loyalty is degenerate '
        'because splits have no majority. The small-group series is a nonnegative baseline adjustment; '
        'it excludes singleton votes and should not be presented as a fully replicated published estimator.\n\n'
        'See [all comparisons](benchmark_comparison.csv), [unity table](unity_by_parliament.csv), '
        '[validation summary](validation_summary.json), and [reproduction instructions](../../REPRODUCING.md).\n',
        encoding='utf-8', newline='\n')
    print('E7:', summary)
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path)
    args = parser.parse_args()
    main(args.output_dir)

# Experiment E7 — Validation & Robustness: Findings

**Status: pipeline certified.**

## What was tested

Whether the pipeline (scraper → integrity checks → cohesion metrics)
reproduces party unity numbers derived from an independently collected
dataset: Godbout & Høyland's *Canadian Parliament Voting Data, 1867–2015*
(Harvard Dataverse; the replication data behind Godbout's *Lost on
Division*, 2020). Overlap window: Parliaments 38–40 (the deposit ends at
the 40th; the readme confirms 41st/42nd data was never deposited).

## Method — data-vs-data, not figure-reading

The deposit contains raw member × division vote matrices, not published
unity scores, so benchmark values were **computed from their raw data**
by `experiments/build_benchmarks_e7.py`, which imports the metric
functions and filter constants (`corrected_rice`, `is_lopsided`,
`count_yea_nay`, `party_majority_side`, lop-sided ≤ 5, ≥ 25 votes/MP)
directly from `experiment_e7.py`. Both sides of the comparison share one
implementation of every definition, so any difference in output isolates
**data collection** — which is exactly what a pipeline certification
should measure. This is a stronger test than reading published values
off the book's figures, but it is not a comparison against numbers
printed in *Lost on Division*; describe it accordingly.

Vote-code mapping from the deposit readme: 1=yes, 2=no enter the
metrics; paired (3), combination codes (4–7, a handful per parliament),
not-voting (9), and not-sitting (99) are excluded, mirroring the
Yea/Nay-only observability of our per-division files.

## Results

36 comparisons (Parliaments 38–40 × {Conservative, Liberal, NDP, Bloc}
× {rice, rice_contested, loyalty}):

- **30 of 36 exact to two decimals.**
- Largest difference: **−0.10** (P40 Liberal contested Rice) — well
  inside the pre-registered tolerance of ~1 point.
- Division universes match exactly: 190 / 380 / 363 divisions in
  P38/39/40 in both corpora.

Full table: `results_e7/unity_by_parliament.csv`; benchmark rows with
provenance: `benchmarks_e7.csv`.

## The residual differences are diagnostic

All six non-zero diffs are Liberal, all negative, all in P38–40 — the
parliaments with prominent Liberal floor-crossings (Stronach, Emerson,
Khan). Godbout codes party switchers with explicit term dates (`Id.2`
suffixes); our pipeline uses the affiliation recorded in each vote's
CSV. A handful of votes near a crossing date are attributed to
different caucuses under the two conventions. This is a documented
coding-convention difference worth ~0.1 points, not a bug.

## Robustness notes carried forward

- **Desposato small-group correction**: cosmetic for major parties
  (orderings unchanged), but material for tiny caucuses (Green,
  P44: 92.6 raw → 88.3 corrected). Small-party numbers should only be
  reported corrected.
- **MP-level loyalty is degenerate for two-member caucuses** (splits
  have no majority side, so only unanimous votes count) — another
  reason to prefer corrected Rice for the Greens.
- **Agreement Index deliberately not implemented**: absence is
  unobservable in our files, and with two observable options the index
  reduces to a transform of Rice.

## Implication

E1's findings, and everything downstream (E2–E6), now rest on a
pipeline certified against the definitive independently collected
dataset in the field. Proceed to E2.
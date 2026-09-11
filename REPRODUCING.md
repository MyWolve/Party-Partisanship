# Reproducing Party Partisanship

## Supported environment

The reference run uses Python 3.12 on Windows. Use a fresh virtual environment and install `requirements-lock.txt`; `requirements.txt` delegates to that same lock. The exact interpreter patch, platform, packages, code hashes, and corpus hash are saved in `audit/run_manifest.json`. Numerical tables use fixed ordering, explicit rounding, UTF-8, and LF endings. PNG rendering may vary with platform/font libraries; numerical identity is the cross-environment contract. The repeat check separately records whether image bytes matched on the reference machine.

Installation is the only network step in normal reproduction. The evidence download script and the original scraper are separate, explicitly invoked tools. Do not run a live scrape to reproduce this snapshot.

## One command audit

After creating a virtual environment and installing the lock as shown in the README:

```text
python reproduce.py --check --repeat
```

This command performs the following stages and fails on the first unsuccessful stage:

1. Verify input file membership and SHA256 digests against `audit/input_manifest.json`.
2. Rebuild every source repair from frozen evidence and compare the result with the registered decisions.
3. Run the hand-calculated and failure-path tests.
4. Check metadata/member coverage, CSV schemas, identities, dates, and exact official flag totals in all 13 sessions.
5. Rebuild all 36 benchmark values from the deposited matrices and compare their CSV records with the baseline without overwriting it.
6. Run E1 and E7 into temporary directories. Each experiment also performs its own integrity preflight.
7. Run both experiments a second time and compare the generated tables and findings. Compare PNG bytes separately.
8. Verify that the inputs did not change during execution, then compare the generated tables and findings with the saved results.

A failed integrity check or benchmark comparison cannot replace experiment outputs. `--check` leaves saved analytical outputs intact; the separate run manifest and validation log are refreshed to describe the completed audit. A failure leaves any previous manifest as a historical record, not a success record for the failed attempt.

To regenerate outputs after a deliberate reviewed change:

```text
python reproduce.py --repeat
```

Results are staged and copied into `experiments/results_e1` and `experiments/results_e7` only after the preceding checks succeed. This protects against analytical validation failures, not hardware failure during the final file copies.

## Individual commands

```text
python tools/build_audit_data.py --check
python -m unittest discover -s tests -v
python check_data.py --output audit/integrity.json
python experiments/build_benchmarks_e7.py --check
python experiments/experiment_e1.py
python experiments/experiment_e7.py
```

The experiment scripts accept `--output-dir PATH`. Both stop before writing results when the corpus is invalid. E7 also rejects missing, duplicate, invalid, unexpected, or out-of-tolerance benchmark records before output creation. Do not invoke the audit builder with Python optimization (`-O`); its evidence assertions must remain enabled, and it explicitly rejects that mode.

## Data contract

Raw parliamentary CSVs and XMLs are preserved. `audit/data_decisions.json` binds each correction to the exact raw member file and metadata row. A changed source record requires re-audit. `vote_data.py` applies the following evidence-based transformations in memory:

- Seventeen divisions regain dual Yea/Nay coding from official XML. Both flags contribute to the official tally check; the member-division contributes to neither side in binary analysis.
- Division 42-1/871 is reconstructed from the Journals. Names are uniquely matched to a same-sitting official roster for identifiers and affiliations; no votes are copied from that roster.
- Division 42-1/724 gains the Journal-recorded Yea vote of Monique Pauzé. Adjacent-day minor-group labels differ, but both map to this project's Independent aggregate. The exact June 5 label is not inferred.

`tools/build_audit_data.py` checks identities, coverage, votes, totals, source hashes, and uniqueness when rebuilding these decisions. The original empty file and incomplete member record remain available for comparison.

Unknown schemas, duplicated member identifiers, duplicated division metadata, missing member files, orphan files, invalid counts, and unregistered discrepancies are errors. Business-category uncertainty is a separate warning and is handled in E1 sensitivity outputs; it is not a data-tally exception.

Input hashes normalize CRLF to LF for text outside `evidence/`. Evidence is hashed byte-for-byte and Git marks it as non-text to preserve the retrieved bytes. A digest identifies the reviewed snapshot; it does not prove that a remote source was historically correct. Source URLs and the retrieval date accompany the archived material in `evidence/sources.json`.

## Metric definitions

Rice = 100 × |Yea − Nay| / (Yea + Nay). Majority share = 100 × max(Yea, Nay) / (Yea + Nay). Neither is defined when no binary votes are observed. Dissent is at least one binary voter opposing the observed party majority; ties are omitted from this outcome and from MP loyalty.

E1 gives each eligible division equal weight. The main comparison excludes documented free stages for the relevant party. It includes unresolved whip status where a known business category exists, then separately reports removal of those cases. `unknown_bill_as_government` tests the unclassified bill subject. `category_only` retains documented free stages. This prevents a single preferred coding assumption from being presented as the only result.

E1 contested divisions have no more than 95% of observed binary House votes on either side. E7 contested divisions have more than five on each side. Paired and dual-coded observations are excluded before both filters. These filters are intentionally different and are not interchangeable.

E7 averages Rice over divisions with observed party votes. MP loyalty gives each qualifying MP–party record equal weight, requires at least 25 qualifying votes, and uses affiliation recorded per division. The small-group series rescales Rice relative to an independent 50/50 voting baseline, clamps negative adjustments to zero, and omits singleton divisions. It is a descriptive adjustment, not a claim to reproduce a complete published estimator. Two-member caucus loyalty can be 100% by construction because tied divisions are omitted.

## Output schemas

| File | Unit and key fields |
| --- | --- |
| E1 `summary.csv` | Session × party × category × scope × variant; divisions, with_dissent, dissent_rate |
| E1 `classification_audit.csv` | Division × party; category, stage, source of bill type, documented status and scope, majority definition, dissent count |
| E1 `sensitivity.csv` | Pooled governing-party comparison × scope × variant; both denominators, counts, rates, ratio |
| E1 `outliers.csv` | Governing-party government-bill divisions with dissent; names and status included for inspection |
| E1 `headline.json` | Main comparison and counts used by the generated findings |
| E7 `unity_by_parliament.csv` | Parliament × party; Rice variants, loyalty, qualifying MP count, contested House-division count |
| E7 `benchmark_comparison.csv` | Parliament × party × metric; observed/reference values, difference, tolerance, pass status, source |
| E7 `validation_summary.json` | Expected comparison count, exact matches, largest difference, tolerance, overall status |

The E7 `divisions` field is the total contested House division universe for that parliament, not a party-specific denominator. Empty rate cells mean undefined, not zero. E1 rates and ratios are rounded to six decimals; findings display two. E7 values retain the historical two-decimal definition. The benchmark tolerance is **1.00 percentage point**, inclusive; 1.01 fails. Exact matches and maximum difference remain visible so smaller changes are not hidden by that tolerance.

## Updating the snapshot deliberately

Make changes in a separate branch. Retrieve new evidence explicitly with `tools/fetch_audit_evidence.py`; existing snapshots are preserved. A live scrape is a data update and needs its own review. Re-audit affected source decisions and regenerate derived files with `tools/build_audit_data.py`. Inspect changes before using `tools/freeze_inputs.py --write` to register a new corpus. Ordinary reproduction only verifies the manifest and never accepts a new one automatically.

The full-session gate expects the current 13-session universe. Adding another session requires updating the session list and governing-party map along with the manifest and tests. Neither a new baseline nor a larger tolerance should be introduced merely to make a failing comparison pass.

After the deliberate update, run `python reproduce.py --repeat`, review the numeric and visual differences, then run `python reproduce.py --check --repeat`. Record changed denominators and conclusions in the implementation audit. The code fingerprint disambiguates uncommitted work from the base Git revision.

## Separate collection and session diagnostics

Collection is deliberately separate from reproduction. Choose a new output directory:

```text
python can_scrape.py --session 40-1 --output incoming/40-1-review
python visualize_parliament.py --session 38-1 --output-dir diagnostics/38-1
```

The collector refuses existing output directories. It saves the raw responses and a collection manifest, validates schemas and exact tallies, and verifies that session metadata stayed stable during the run. Failures return a nonzero exit and retain a failed manifest for diagnosis. `validated_raw_snapshot` is not permission to replace the frozen corpus: bill metadata, source discrepancies and historical corrections still need review before promotion. Incoming snapshots and exploratory diagnostics are ignored by Git.

The diagnostic command requires an explicit session and validates it before generating charts with a noninteractive backend. E7 and session loyalty reports use Person IDs so name or constituency changes do not split one MP into multiple records. Default single-division loaders still return display names; longitudinal callers should pass `member_ids=True` or use `load_member_history`.

The GitHub workflow runs the full offline reproduction check on Windows, Ubuntu and macOS after dependency installation. Actions are pinned to immutable revisions; workflow files are included in the tested-code fingerprint. Successful jobs upload their run manifest and validation log. The latest PR checks are the authority on platform outcomes.

See [collection and legacy review](audit/COLLECTION_AND_LEGACY_REVIEW.md) for repairs, live-test scope, API changes and the remaining verification register.

## Record-level comparison and bill refresh

[The record-level review](audit/RECONCILIATION_REVIEW.md) now covers all 933 divisions in the comparison deposit: 256,676 joined observations match vote flags and analytic party, with one extra deposit observation and one sitting/calendar date difference documented. `reproduce.py` also checks the saved crosswalk and discrepancy outputs.

Use `python tools/collect_bills.py --session 40-1 --output incoming/new-bill-review` for a separate bill refresh snapshot. The shared parser supports archived and current LEGISinfo schemas and refuses unknown schemas. The historical live check exposed missing sponsors in the new response; no bill archive was replaced. See the review for an offline replay command and evidence.

## Later-session and bill coverage checks

The [source coverage review](audit/SOURCE_COVERAGE_REVIEW.md) checks 35 fixed later-session divisions (10,178 matching member records) and bill exports across all 13 sessions. All 4,411 historical bill numbers/types/titles agree, but the new exports lose their sponsor names, so historical archives are retained. A reviewed 45-1 supplement replaces numbering inference for 107 divisions without changing categories.

`python tools/review_source_coverage.py --check` reproduces the saved comparison tables offline and is included in `reproduce.py`. The separately invoked `--fetch` mode retrieves absent snapshots and verifies existing hashes. This sample is a same-publisher format/stability check, not full independent verification of later parliaments.

# Later-session source coverage and bill archive review

Subsequent update: [sponsor recovery](SPONSOR_RECOVERY_REVIEW.md) restores bill-level sponsor names and official Person IDs through separately archived interfaces. The bulk-export sponsor omissions documented below remain observable; richer original archives are preserved.

## Outcome

A fixed later-session XML sample matches the frozen corpus, and bill-refresh coverage is now checked across all 13 sessions. The review also closes a concrete archive gap: 45-1 now uses a reviewed official bill-type supplement instead of relying solely on numbering inference. Original exports and historical bill XMLs remain untouched.

## Later-session vote sample

The selection takes the first, quarter, middle, three-quarter and last division by sorted division number in each session from 41-1 through 45-1. The exact rule and 35 selected records are in [source_review_selection.json](source_review_selection.json). The executable review regenerates this selection and refuses a changed sample.

All **10,178 member observations across 35 divisions** match the freshly retrieved XML on Person ID, Yea/Nay/paired flags, and raw party label. Dates and decision results also match in all 35 cases. [The sample table](source_coverage/vote_sample.csv) lists denominators and outcomes; [the difference table](source_coverage/vote_differences.csv) has no discrepancy rows.

This is a purposive coverage check spanning seven sessions and different points within each session. It covers 35 of 3,918 later-session divisions, not the full later corpus. It is not random and supports no statistical error-rate claim. XML and CSV are different exports from the same publisher; agreement checks format consistency and source stability, not independent historical truth. The independent deposited comparison remains limited to Parliaments 38–40.

The archived XML parser now rejects unexpected roots/records, missing or duplicate fields, wrong division/session identifiers, malformed dates/flags, duplicate Person IDs, and empty/inconsistent exports. These failures are tested. No source differences were hidden by a tolerance or repair in this sample.

## Bill coverage across sessions

Across the 12 historical session archives, all **4,411 bill numbers, types and titles** match the current session-wide LEGISinfo exports. There are no additions, removals, type changes or title changes in those sessions. However, **all 4,411 previously populated sponsor fields are blank in the new exports**. This establishes that the 40-1 sponsor loss was systematic across the historical sessions reviewed, rather than an isolated example.

[Bill coverage](source_coverage/bill_coverage.csv) reports counts by session. [Field-level changes](source_coverage/bill_changes.csv) preserves each lost value and the new empty value. Source URLs, retrieval dates and hashes are in the evidence ledger. Existing historical archives are retained; the new responses are not promoted over richer records. The review does not establish why the publisher's current export omits sponsor fields.

## Closing the 45-1 gap

Neither `House of Commons/45-1.xml` nor 45-1 records in `all.xml` existed in the frozen archive. The new official export contains 185 bills and covers all 39 bill numbers directly referenced in the session's metadata. The classification comparison additionally handles bill numbers recovered from subjects.

The [per-division upgrade table](source_coverage/classification_upgrade.csv) compares old numbering-based classification with the new official lookup. **107 divisions move from `number_inference` to `legisinfo`; no category changes.** The other 66 divisions retain their existing non-bill/unknown source status. E1 counts, rates and sensitivity results are unchanged, as are E7's metrics and benchmark results.

`load_bill_types('45-1')` now explicitly uses [the reviewed supplement](../evidence/legisinfo-45-1-current.xml) when the original session archive is absent. Missing supplementary evidence is an error, not a silent return to inference. This is a frozen, dated supplement, not a live lookup. Its sponsor fields are also empty; the loader does not invent sponsor names. Historical archives retain priority.

Only type/title lookup is improved. Confidence status and free-vote instructions are not inferred from the mere availability of a bill record. The supplemental export includes bills introduced after some recorded divisions; this audit does not use changing status or sponsorship to make historical claims.

## Reproduction and validation

```text
python tools/review_source_coverage.py --check
python reproduce.py --check --repeat
```

The full reproduction command now checks coverage tables alongside data integrity, member reconciliation, tests, benchmarks and experiments. The suite contains 55 tests. The input manifest deliberately includes the fixed selection and the added evidence snapshots. E1's classification audit changes its source labels for 45-1; numerical findings do not change. Source URLs and bytes can be inspected without network access.

`python tools/review_source_coverage.py --fetch` is a separate network operation. It verifies existing snapshots and never overwrites them. New remote-state studies should use distinct filenames and a reviewed manifest update; this archive records this review's date.

## Remaining open work

- Independent historical corroboration of later-session records beyond this limited same-publisher sample.
- Resolving historical free-vote/stage instructions and minor-group labels where the current evidence remains insufficient.
- Recovering complete current/historical sponsor data from an authoritative source before any wholesale archive replacement.
- Research-design extensions: bill-level weighting, caucus-size effects and remaining experiments.

These remain source or methodological questions. The executable collection, schema, integrity, identity, reconciliation and coverage checks now make future changes reviewable without claiming those questions are already answered.

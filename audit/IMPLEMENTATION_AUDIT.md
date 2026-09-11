# Implementation audit — 11 September 2026

The approved actions A1–A6 are implemented on `codex/reproducibility-audit`, against reviewed revision `77248bcc97617eb07593723dc8144d9121acb038`. The original parliamentary CSV/XML exports and deposited benchmark matrices are preserved. Changes are local and have not been pushed, merged, or published.

## What changed and why

| Action | Implementation | Evidence and validation |
| --- | --- | --- |
| A1 — Resolve division 871 and enforce validation | Reconstruct its 306 votes from the official Journals, joining names uniquely to the same-sitting division 872 identity roster. Require preflight before E1/E7 output. | Journals give 172 Yea and 134 Nay. Offline reconstruction checks every name, total, and source fingerprint. Tests prove failed preflight preserves existing outputs. |
| A2 — Replace tally tolerance | Replace the blanket tolerance with 19 explicit, source-bound repairs and exact tally checks. Restore 38 dual Yea/Nay observations across 17 divisions; append the missing Pauzé vote in division 724. | The full [decision ledger](DATA_DECISIONS.md) explains each repair. Both small and large unlisted mismatches fail. Original files remain untouched. |
| A3 — Make E7 executable | Require the complete set of 36 unique, finite benchmark comparisons within the declared 1.00 percentage-point tolerance. Check benchmark reconstruction without overwriting it. | All 36 now agree exactly at two decimals. Missing, duplicate, invalid, unexpected, and out-of-tolerance comparisons fail. Independent hand-calculated fixtures check core arithmetic. |
| A4 — Audit classifications | Encode sourced party, stage, and backbench/cabinet scope; retain unresolved cases and an unknown-bill category. Publish per-division classifications and sensitivity variants. | [Classification audit](CLASSIFICATION_AUDIT.md), archived sources, party/stage regression tests, and classification CSV. No procedural inheritance based only on a bill number. |
| A5 — Correct interpretation | Rewrite README, findings, chart labels, and comments as descriptive comparisons. Generate findings from the computed outputs. | Claims no longer present business category as a measured causal whip effect or E7 agreement as certification of the entire pipeline. |
| A6 — Reproduce and present | Add a dependency lock, offline reproduction command, frozen input manifest, code/output hashes, repeat checks, machine-readable results, and this report. | Fresh Python 3.12.14 environment; 30 regression tests; exact corpus checks across 13 sessions; two complete runs; saved-result comparison. |

## Before and after

| Measure | Reviewed baseline | Audited result |
| --- | ---: | ---: |
| Corpus integrity | Failed: empty division 871; 18 other discrepancies tolerated | Pass: 19 documented repairs, no blanket tolerance |
| Governing-party government-bill divisions with dissent | 50 / 1,502 (3.33%) | 41 / 1,491 (2.75%) |
| Private-members-business divisions with dissent | 225 / 848 (26.53%) | 225 / 848 (26.53%) |
| Private/government dissent-rate ratio | 7.97 | 9.65 |
| Supply divisions with governing-party dissent | 1 / 1,118 | 1 / 1,118 |
| E7 exact comparisons at two decimals | 27 / 36 | 36 / 36 |
| E7 maximum absolute difference, percentage points | 0.10 | 0.00 |

The E1 denominator change is traceable: restore one C-38 stage previously excluded without adequate scope evidence; add reconstructed division 871; move malformed division 247 to unknown bill; exclude 12 documented C-14 free-vote divisions. Thus 1,502 + 1 + 1 − 1 − 12 = 1,491. The restored C-38 division adds one dissent division, and the C-14 exclusions remove ten: 50 + 1 − 10 = 41. The main comparison excludes 22 documented free governing-party divisions overall and retains 10 explicitly unresolved governing-party divisions.

Classification matters: the category-only ratio is 6.58; excluding documented free votes gives 9.65; additionally excluding the audited unresolved cases gives 12.29. These are sensitivity analyses, not competing causal estimates. The full [sensitivity table](../experiments/results_e1/sensitivity.csv) also reports contested-division variants and the unknown-bill alternative.

## Additional defects caught during implementation

The first metric repair excluded dual Yea/Nay rows and brought E7 to 33 exact matches. The subsequent audit found 215 paired-plus-binary observations still entering binary metrics. Excluding those as well brought agreement to 36/36. Across the corpus, all 253 combination-coded observations are now explicitly listed in [the integrity report](integrity.json). Official tally verification still counts each recorded flag; binary analysis requires exactly one unpaired Yea or Nay.

A source download returned a government archive interstitial under a PDF filename. The audit replaced it with the actual 446,168-byte PDF after following the archive session, checked its PDF signature, and recorded the correction in the source ledger. Retrieval now rejects PDF/HTML mismatches and altered archived hashes, and preserves original retrieval dates. Reproduction uses the archived bytes and never fetches live sources.

## Reproduction and audit evidence

Follow [REPRODUCING.md](../REPRODUCING.md). The final verification command is:

```powershell
.\.venv\Scripts\python.exe reproduce.py --check --repeat
```

The command verifies 4,927 registered input files, rebuilds the audit derivations, runs the 30 tests, validates all 13 sessions, reconstructs all 36 benchmark rows, and executes E1 and E7 twice. The two runs produce identical numerical tables, findings, and PNG bytes in the tested environment. Regenerated tables and findings match the saved results. [run_manifest.json](run_manifest.json) records exact environment, dependency versions, code hashes, input hashes, output hashes, and repeat status; [validation_log.txt](validation_log.txt) retains the check output.

The frozen corpus SHA256 is `5f930ceff3617e933c8cecddfe1f1f302abeb933bde90a9fa8ffd969ba00e78a`. Text hashes normalize CRLF to LF; archived evidence uses byte hashes. The Git revision in the run manifest identifies the base checkout; the individual code fingerprints identify the tested implementation, including uncommitted changes at execution time.

Charts use clear styling, explicit denominators and scope, and readable labels. Findings and tables are generated together to avoid stale manually copied results. E7's chart uses a restricted axis to show small differences; its scale is stated explicitly. Byte-identical PNGs are demonstrated within this Windows environment; cross-platform font/rendering identity is not claimed.

## Remaining limits

- Division 871 identities and party affiliations rely on the same-sitting 872 roster. Vote choices come exclusively from the Journals, and every identity match must be unique.
- Pauzé's exact minor-group label on June 5, 2018 remains uncertain between adjacent-day labels. Both map to the existing Independent analytic category. This assumption is explicit in the repair ledger.
- C-30, C-17, certain later stages, and division 247 remain unresolved. The sensitivity outputs expose their effect. Category proxies elsewhere are not independently confirmed whip instructions.
- Liberal free-vote evidence concerns backbenchers. Caucus-level exclusion is not a backbencher-only estimate and does not identify cabinet membership per vote.
- Agreement with the deposited data uses shared metric definitions. Hand-calculated tests provide separate arithmetic checks, but neither establishes a causal whip effect.
- The corpus is a frozen snapshot, including an incomplete 45-1 session. Only the fresh Windows/Python 3.12.14 environment was executed here. E2–E6 and live-data refresh remain outside this implementation.

These limitations are documented research boundaries. They are not concealed by relaxing data validation.

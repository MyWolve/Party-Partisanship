# Party Partisanship

**Where does party unity hold, and where does room for dissent appear in Canada's House of Commons?**

This project studies observed cohesion and dissent across **4,851 recorded divisions in 13 sessions, 38-1 through 45-1**. The final session is an incomplete snapshot. Original exports are preserved; a [corrected dataset and dictionary](data/README.md) make 1,343,065 member observations available for reuse. All results reproduce offline from frozen sources.

## What the results show

Governing-party dissent appears much more often on private members' business than on government bills or supply. The main E1 comparison excludes documented free-vote stages for the governing party:

| Business | Divisions containing dissent | Rate |
| --- | --- | --- |
| Government bills | 41 / 1,491 | 2.75% |
| Private members' business | 225 / 848 | 26.53% |
| Supply | 1 / 1,118 | 0.09% |

A division counts once if at least one binary voter opposes the observed governing-party majority. These percentages describe divisions, not the share of MPs dissenting. Session 40-1 is excluded from E1 because it has only one division.

The private/government ratio is **9.65** under the main classification. Alternative all-division classifications produce **6.58–12.29**; this is a sensitivity range, not a confidence interval. [Counts and scope sensitivity](experiments/results_e1/FINDINGS_E1.md)

Several concrete patterns stand out in that same main scope:

- **658 consecutive eligible Conservative government-bill divisions without dissent**, from 39-2/113 on **27 May 2008** to 41-2/467 on **18 June 2015**. This counts eligible government-bill divisions, not every House vote.
- **Harper-era government bills: 2/762 (0.26%)**, versus **30/669 (4.48%) under Trudeau and Carney**, a **17.09-fold** difference in observed dissent incidence across those pooled periods.
- **Martin's 38-1 session has the highest government-bill rate: 9/60 (15.00%)**, among sessions with at least 30 eligible government-bill divisions. Supply dissent is rare across the sample: **1/1,118 (0.09%)**.
- **C-89, 42-1/950: six Liberal dissenters** on postal-services legislation. It is the largest episode not already flagged unresolved and a candidate for further investigation; a whip instruction still needs a source.

See [the generated narrative, session table and ranked dissent episodes](experiments/results_e1/FINDINGS_E1.md#what-stands-out).

This is evidence about voting patterns by business category. It does not identify the causal effect of a whip instruction. Party policy, issues, participation, caucus size, and repeated votes on a bill also matter.

![Governing-party dissent by session](experiments/results_e1/whip_test_by_session.png)

The chart shows how the pooled comparison varies across sessions; bar labels retain the denominators. Different sessions contain different business and participating MPs, so this is not a controlled time trend.

**Repeated bills change the magnitude.** When each session–bill receives equal weight, its mean fraction of divisions containing dissent is **5.15% for government bills** and **32.71% for private members' bills**. The private comparison includes 663 numbered-bill divisions and excludes 185 unnumbered divisions, including motions. On the same numbered subset, weighting every division equally gives 29.41% for private business. The broad contrast survives this check, but its magnitude depends on the unit and population. [Bill-weighting results](experiments/results_e1/design_checks.csv)

**Dissent is also a question of intensity.** Minority votes account for **0.065% of eligible governing-party member-votes on government bills**, versus **1.741% on private members' business**. These use member-vote denominators, unlike the table above. The division-level contrast persists in both larger observed-party-voter bands (101–150 and 151+); the 1–100 band has only 3 government and 5 private divisions. These descriptive checks do not estimate an effect of caucus size. [Participation checks and definitions](experiments/results_e1/FINDINGS_E1.md#repeated-bills-and-participating-caucus-size)

## How much has been verified?

E7 compares aggregate metrics with values computed from Godbout and Høyland’s deposited raw voting matrices for Parliaments 38–40. **36 of 36 comparisons match to two decimals**, and the maximum difference is **0.00 percentage points**. Shared definitions make this a data-agreement check, not an independent validation of the arithmetic or whip classifier. [Full E7 findings](experiments/results_e7/FINDINGS_E7.md)

Record-level comparison across those parliaments matches **256,676 joined observations**, with one extra deposit observation and one sitting/calendar date discrepancy documented. Later-session checking matches **10,178 observations in 35 sampled divisions** against official XML. That purposive same-publisher sample does not establish independent accuracy throughout later sessions. All 13 sessions pass exact internal integrity checks.

## From collection to findings

| Stage | Tool | What it establishes |
| --- | --- | --- |
| Collect separately | `can_scrape.py`, `tools/collect_bills.py` | New raw snapshots, response provenance, schema/tally checks; no automatic promotion |
| Review sources | `tools/build_audit_data.py`, `tools/reconcile_members.py`, `tools/review_source_coverage.py` | Evidence-bound repairs, member comparisons, bill changes and limited later-session coverage |
| Register a reviewed snapshot | `tools/freeze_inputs.py --write` | Explicitly records approved input membership and hashes; never repairs a failing comparison by itself |
| Reproduce and export | `reproduce.py --check --repeat` | Tests, integrity, source comparisons, E1/E7 and corrected export match saved results and repeat |
| Interpret | E1/E7 findings and sensitivity tables | Descriptive conclusions with visible denominators and remaining uncertainty |

Live vote collection has been demonstrated on the one-division 40-1 session; larger live refreshes still need review. Bulk bill exports omit sponsor fields, but [sponsor recovery](audit/SPONSOR_RECOVERY_REVIEW.md) now links all **4,596 bills to 783 official Person IDs** using sponsor-filtered records and direct-detail checks. Original sponsor labels remain available, and dated sponsor histories are not inferred. See [the workflow and update procedure](REPRODUCING.md).

## Reproduce the results

Use **Python 3.12** in a fresh virtual environment. The dependency lock includes exact transitive versions.

```text
python -m venv .venv
```

Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.\.venv\Scripts\python.exe reproduce.py --check --repeat
```

macOS or Linux:

```sh
.venv/bin/python -m pip install -r requirements-lock.txt
.venv/bin/python reproduce.py --check --repeat
```

Dependency installation needs network access. Reproduction does not. The command verifies the frozen inputs, rebuilds the source repairs, runs regression tests, validates the corpus, checks the benchmark reconstruction, runs both experiments twice, and compares the numerical tables and findings with the saved outputs. It records the environment and hashes in [the run manifest](audit/run_manifest.json).

Read [REPRODUCING.md](REPRODUCING.md) for the data contract, commands, output schemas, limitations, and update procedure.

## Read the work

| Document | Purpose |
| --- | --- |
| [Sponsor recovery](audit/SPONSOR_RECOVERY_REVIEW.md) | Bill-to-Person-ID links, source discrepancies, direct-detail checks and temporal limits |
| [Current project review](audit/PACKAGING_AND_STORY_REVIEW.md) | Dataset packaging, denominator checks, current findings and open work |
| [Dataset dictionary](data/README.md) | Corrected tables, joins, provenance, versions and citation guidance |
| [Implementation audit](audit/IMPLEMENTATION_AUDIT.md) | Changes against the reviewed baseline, evidence, tests, and remaining uncertainty |
| [Collection review](audit/COLLECTION_AND_LEGACY_REVIEW.md) | Collector lifecycle, stable identifiers and live-test scope |
| [Record reconciliation](audit/RECONCILIATION_REVIEW.md) | Earlier-session member comparisons and bill refresh behavior |
| [Source coverage](audit/SOURCE_COVERAGE_REVIEW.md) | Later-session sample, sponsor loss and the 45-1 supplement |
| [E1 findings](experiments/results_e1/FINDINGS_E1.md) | Dissent by category, scope sensitivity, and interpretation |
| [E7 findings](experiments/results_e7/FINDINGS_E7.md) | Benchmark agreement, metric definitions, and limits |
| [Data decisions](audit/DATA_DECISIONS.md) | Why each source repair is necessary and how it is reproduced |
| [Classification sources](audit/CLASSIFICATION_AUDIT.md) | Verified free-vote scope and unresolved historical questions |

## Repository map

```text
Parliament_<P>-<S>/          Original member CSVs and division metadata
House of Commons/           Original LEGISinfo XML bill archive
experiments/experiment_7_data/  Deposited comparison matrices and codebook
vote_data.py                Strict parsing and explicit source repairs
bill_info.py                Business classification and sourced party/stage status
check_data.py               Integrity gate with no blanket tally tolerance
visualize_parliament.py     Cohesion, dissent, loyalty, and legacy plotting helpers
experiments/                E1, E7, benchmark builder, and generated results
reproduce.py                Offline reproduction and repeatability audit
audit/                      Decisions, hashes, test evidence, and reports
evidence/                   Frozen official XML, Journals, and historical sources
data/                       Corrected reusable export, dictionary and manifest
tests/                      Hand-calculated and failure-path regression fixtures
tools/                      Explicit evidence retrieval and audit reconstruction
```

## Research boundaries

- Party dissent means a binary vote against the observed caucus majority. It is not automatically defiance of a whip. Tied caucus divisions have no majority and are omitted from dissent and loyalty calculations.
- Official dual-coded votes count on both sides when checking announced tallies. They are excluded from binary metrics. Paired votes are also excluded.
- C-38 and C-14 free-vote records are party- and stage-specific. Liberal backbench freedom does not imply cabinet freedom. Caucus-level exclusions do not measure backbencher-only behavior.
- C-30, C-17, some later-stage scope, and the malformed subject in 42-1 division 247 remain explicit uncertainties. They are not silently classified as verified whipped votes.
- Session 40-1 is omitted from E1 because it has one division; E7 includes it when pooling Parliament 40. The 45-1 snapshot is incomplete and is not a live feed.
- The two experiments use different contested-division filters: E1 uses a 95% majority-share threshold; E7 requires more than five binary votes on each side. Their definitions are retained and documented separately.

## Next research

E1 and E7 have been implemented and audited. E2—trends over time—remains next. E3–E6 cover government status, concentration of dissent across MPs, confidence-related business, and voting stages. These analyses are not included in this repair and reproducibility update.

## Sources

The [House of Commons vote exports](https://www.ourcommons.ca/members/en/votes), [Journals](https://www.ourcommons.ca/DocumentViewer/en/house/latest/journals), and [LEGISinfo](https://www.parl.ca/legisinfo/en/overview) provide the parliamentary records. The comparison deposit is Godbout and Høyland’s *Canadian Parliament Voting Data, 1867–2015*; the included Parliaments 38–40 subset and its [codebook](experiments/experiment_7_data/readme.txt) are retained for offline reproduction. Benchmark values are computed from those matrices, not transcribed from published figures.

For citation and the unresolved project-wide license choice, see [dataset reuse guidance](data/README.md#versions-verification-and-citation).

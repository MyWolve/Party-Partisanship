# Party-Partisanship

How strong are party lines in Canada's House of Commons, and when do MPs dissent?

This small Python project collects recorded votes, checks their totals, and compares party voting on one bill, several bills, types of business, or whole parliaments. The included snapshot covers **4,851 divisions from 38-1 through 45-1**; 45-1 is incomplete.

The question is about whipping and conscience. The observable result is whether an MP voted against their party's majority. Agreement can reflect shared beliefs as well as discipline; dissent can occur on a permitted free vote. These records cannot reveal personal motives or establish a whip instruction by themselves.

## Start here

Use Python 3.12. After cloning this repository:

```sh
python -m venv .venv
# Activate: Windows PowerShell: .venv\Scripts\Activate.ps1
# Activate: macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
python check_data.py
python analyze.py --parliament 38 39 --output outputs/compare
```

Open `outputs/compare/dissent.png` for a side-by-side party comparison. Read `summary.csv` for the counts behind it. Every analysis command validates the saved data first and writes to a **new** directory.

## Ask a question

```sh
# One bill, including all its recorded stages
python analyze.py --session 42-1 --bill 42-1/C-89 --group-by bill --output outputs/postal

# Several bills, with a separate result for each
python analyze.py --session 42-1 --bill 42-1/C-89 42-1/C-14 --group-by bill --output outputs/bills

# Government bills versus other parliamentary business, for every party
python analyze.py --session 44-1 --group-by category --output outputs/categories

# An actual LEGISinfo bill type, compared across two parliaments
python analyze.py --parliament 38 39 --bill-type "House Government Bill" --output outputs/government

# Explore titles and vote subjects; inspect the matched divisions
python analyze.py --keyword climate environment --group-by bill --output outputs/topics

# Export the complete corrected snapshot and compare sessions
python analyze.py --group-by session --output outputs/all
```

Multiple keywords mean **any** case-insensitive substring match; different filters combine with **and**. Keyword searches cover the archived long title and division subject, not bill full text or a separately collected subtitle. A subject may mention a topic without the bill primarily addressing it.

A bill key includes the session because numbers restart. One bill can have many divisions; stages remain visible in the export. Parliament selections combine all their sessions. Grouping by bill omits unnumbered business from the summary, but retains it in selected-data exports. Motions and supply are business categories, not bill types.

## How to read dissent

| Measure | Meaning |
| --- | --- |
| Dissent frequency | Percentage of divisions with at least one vote against the party majority |
| Dissent intensity | Minority member-votes as a percentage of member-votes in divisions with a defined party majority |
| Mean Rice cohesion | Average of `100 × abs(Yea − Nay) / (Yea + Nay)` across divisions; 100 is unanimity, 0 is an even split |

Every output includes denominators. Frequency and mean Rice weight divisions equally, so bills with more recorded votes contribute more. Intensity weights member-votes. Paired and dual-coded votes are excluded from binary measures; tied caucus votes have no majority and are excluded from dissent, but enter Rice as zero. A party with no eligible observations has a blank result. Independents remain in the member data but are not treated as one party.

The default includes free-vote stages and all matching business. Party/stage-specific documented statuses are exported for closer inspection; business categories alone are not verified whipping labels. Comparisons are descriptive, not estimates of the effect of a whip or of conscience.

**A small example:** C-89 in 42-1 has three recorded divisions. Two contain Liberal dissent, with eleven minority member-votes across them and six in the largest episode. The bill command above reproduces those counts. Start with an identifiable bill, inspect its stages, then widen the comparison.

## Use the data elsewhere

Each run creates `divisions.csv`, `party_votes.csv`, `summary.csv`, `members.csv.gz`, `manifest.json`, and a chart (up to 30 groups). Unzip the member CSV for a spreadsheet, or load it directly in Python/R. No project-specific loader is needed. [Columns, joins and examples](DATA.md).

Original CSVs remain in `Parliament_<P>-<S>/`. Nineteen source discrepancies are corrected when reading them; raw files are preserved. The small [correction record](audit/DATA_DECISIONS.md) explains the changes and links the official records. Compressed evidence supports just those corrections and the missing 45-1 bill metadata. This is internal tally validation, not independent verification of every historical vote.

## Collect and check

```sh
python can_scrape.py --session 43-1 --output incoming/43-1-new
python -m unittest discover -s tests -q
```

Collection writes a separate snapshot with URLs, retrieval times and hashes. It checks every downloaded tally and rechecks the session listing at the end. Failures remain visibly failed; existing directories cannot be overwritten. Two live downloads of 43-1 on 14 September 2026 UTC returned identical data for all 26 divisions and passed tally checks. This is a short-session demonstration, not a full-corpus live refresh. Live sources can change or contain inconsistencies. Downloaded snapshots require review before replacing the included data; analysis examples above use the included snapshot.

CI runs the tests and full integrity check, then exports the complete dataset as a downloadable `parliament-data` workflow artifact. Artifacts are temporary; the committed sources and command above recreate them.

## Project scope

The original plotting helpers remain in `visualize_parliament.py`. Its historical `analyze_bill` helper selects a division file; use `analyze.py --bill` for a complete bill. `experiments/` preserves the original exploratory work and historical outputs; they are not regenerated or validated by the MVP command and should not be used as its current results.

Sponsor recovery, broader external reconciliation and extended research remain on `codex/reproducibility-audit`, separate from this MVP. The next useful research step is to document instructions for specific dissent episodes, not infer them from vote counts.

Sources: [House votes](https://www.ourcommons.ca/members/en/votes), [LEGISinfo](https://www.parl.ca/legisinfo/en/overview), and official Journals linked in the corrections. Please cite the source, repository commit and selected sessions when reusing an output. This repository does not grant rights to upstream material.

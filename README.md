## Party-Partisanship

A data analysis project on party discipline in the Canadian House of Commons, conducted just for fun!

How strong is party unity? How defined are party lines? Are Whips that successful? Or are there other key players? This repository scrapes every recorded vote from the House of Commons since October 2004, verifies the data against independent totals, classifies each vote by the kind of business being decided (à la: theme of the bill), measures party cohesion and dissent at the party, category, and individual-MP level — and validates the whole pipeline against the definitive independently collected dataset in the field.

## Repository layout

```
Parliament_<P>-<S>/          Vote data, one directory per session (38-1 … 45-1)
House of Commons/            LEGISinfo bill XMLs (type, sponsor, title)
can_scrape.py                Scraper (ourcommons.ca XML/CSV export endpoints)
check_data.py                Integrity checker; gates the pipeline
bill_info.py                 Division classifier (business category, stage, free-vote overrides)
visualize_parliament.py      Cohesion metrics, dissent analysis, plotting
experiments/
  experiment_e1.py           E1: The Whip Test
  experiment_e7.py           E7: Validation & robustness
  build_benchmarks_e7.py     Computes E7 benchmarks from the Godbout & Høyland deposit
  benchmarks_e7.csv          Benchmark values with provenance (parliament,party,metric,value,source)
  experiment_7_data/         Godbout & Høyland, Canadian Parliament Voting Data 1867-2015 (CC0)
  results_e1/                E1 outputs + FINDINGS_E1.md
  results_e7/                E7 outputs + FINDINGS_E7.md
```

## Data

Each `Parliament_<P>-<S>/` directory contains:
- `file_<N>.csv` : how every MP voted on division N (name, affiliation at the time of the vote, Yea/Nay, paired status (mutual abstention from voting))
- `votes_metadata.csv` : one row per division: number, date, subject, bill number, result, and official Yea/Nay/Paired totals from the XML data.

`House of Commons/<session>.xml` holds LEGISinfo bill details used to distinguish government bills from private members' business.

`experiments/experiment_7_data/` is a CC0 copy of Godbout & Høyland's *Canadian Parliament Voting Data, 1867–2015* (Harvard Dataverse) — raw member × division matrices used only to validate this pipeline (see E7).

### Known data issues/quirks

- On ~19 divisions across six sessions, the member-level file contains 1–2 votes fewer than the announced totals. This is largely consistent with votes struck from the record after the call (an MP not in their seat, voting both ways, etc.); the member files reflect the corrected record and are treated as authoritative.
- The official subject lines contain occasional defects such as typos, placeholder text, and bill references missing their numbers. The classifier handles the known cases explicitly, but it's possible I've missed some.
- Party affiliation is recorded per vote, so floor-crossers are scored against whichever caucus they belonged to at the time. (E7 showed this convention differs from Godbout's term-date coding by ~0.1 points at most.)

## Pipeline
```
# Download vote metadata and files
python3 can_scrape.py
# Verify data before analysis
python3 check_data.py
```
`check_data.py` confirms every division has both a metadata row and a member file, re-tallies the votes, and lists any vote subjects the classifier couldn't categorize. It exits non-zero on any hard problems so it can gate the pipeline.

## Analysis
`visualize_parliament.py` provides:
- **Cohesion metrics** : the Rice Index (|yea−nay|/(yea+nay)) and majority-share, per party per division, with averages that exclude divisions a party did not vote in.
- **Dissent analysis** : because party discipline in the House of Commons tends to be strong (such that Rice scores saturate ≥ 99) the more informative statistics are *dissent frequency* (share of divisions with any 'rebel'), rebel counts per division, and per-MP loyalty scores.
- **The Whip Test** : `bill_info.py` classifies every division by business category (government bill, private members' bill, opposition motion, procedural, supply, throne speech, committee report, appointment) plus reading stage and a confidence flag, with a designated-free-vote override list. `print_whip_report()` then cross-tabulates dissent by category, and `mp_loyalty_split()` scores each MP separately on whipped and free business.

Example:
```
from visualize_parliament import print_whip_report, plot_dissent_by_category
print_whip_report("./Parliament_44-1")
plot_dissent_by_category("./Parliament_44-1")
```

## Experiments (roadmap)

1. **The Whip Test — DONE** (`experiments/results_e1/FINDINGS_E1.md`) : governing-party dissent on government bills vs. private members' business. Headline: an 8.0× free/whipped dissent ratio; Harper-era governments dissented on 2 of 762 government-bill divisions, including a 646-division zero-dissent streak; supply 1/1118; Liberal governments whip ~20× looser than Harper's.
2. **Twenty years of discipline — NEXT** : cohesion and dissent frequency across all sessions; secular trend and minority-vs-majority parliaments.
3. **Government-status effect** : the same party's discipline in government vs. opposition / opposition → government transition.
4. **Where is the Rebel Base?!** : concentration of rebellion across MPs; conscience-caucus vs. free-voters; do MPs who later leave a caucus rebel more beforehand?
5. **Confidence Gradient** : does dissent fall as the stakes of the vote category rise?
6. **Stage Effects** : dissent at second reading vs. third reading of the same bills.
7. **Validation and Robustness — DONE** (`experiments/results_e7/FINDINGS_E7.md`) : the pipeline reproduces party unity computed from Godbout & Høyland's independently collected data (Parliaments 38–40) to within 0.10 points — 30 of 36 comparisons exact to two decimals — under shared metric definitions (lop-sided divisions excluded at ≤ 5, MPs under 25 votes dropped from loyalty). Small-group-corrected Rice and MP-vs-vote weighting confirm the main conclusions are robust.

Per-session statistics exclude Parliament 40-1 (a single recorded vote before the 2008 prorogation). Dissent-rate analyses are run both with and without near-unanimous divisions as a robustness check.

## Longer-term ambitions

Extending to other voting bodies such as the UK House of Commons, and the United States House of Representatives and Senate.

## Requirements
Python 3.10+ with `requests` and `matplotlib` (see `requirements.txt`).

## Acknowledgements

Validation data: Godbout, Jean-François and Bjørn Høyland. 2017. *Canadian Parliament Voting Data, 1867–2015.* Harvard Dataverse (CC0). See also Godbout, *Lost on Division: Party Unity in the Canadian Parliament* (University of Toronto Press, 2020).
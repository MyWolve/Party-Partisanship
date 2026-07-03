## Party-Partisanship

A data analysis project on party discipline in the Canadian House of Commons, conducted just for fun!

How strong is party unity? How defined are party lines? Are Whips that successful? Or are there other key players? This repository scrapes every recorded vote from the House of Commons since October 2004, verifies the data against independent totals, classifies each vote by the kind of business being decided (a la: theme of the bill), and measures party cohesion and dissent at the party, category, and individual-MP level.


## Data

Each `Parliament_<session>/` directory contains:
- `file_<N>.csv` : how every MP voted on decision N (name, affiliation at the time of vote, Yea/Nay, paired status (mutual abstention from voting))
- `votes_metadata.csv` : one row per bill: number, data, subject, bill number, result, and official Yea/Nay/Paired totals from the XML data.

`House of Commons/<session>.xml` holds LEGISinfo bill details (type, sponsor, title) used to distinguish government bills from private members' business. 

### Known data issues/quirks

- On ~19 divisions across six sessions, the member-level file contains 1-2 votes fewer than the announced totals. This is largely consistent with votes struck from the record after the call (an MP not in their seat, voting both ways, etc.); the member files reflect the corrected record are are treated as authoritative.
- The official subject lines contain occassional defects such as typos, placeholder text, and bill references missing their numbers. The classifier handles the known cases explicitly, but it's possible I've missed some.
- Party affiliation is recorded per vote, so floor-crossers are scored against whichever caucus they belonged to at the time. 

## Pipeline
```
# Download vote metadata and files
python3 can_scrape.py 
# Verify data before analysis
python3 check_data.py
```
`check_data.py` confirms every bill has both a metadata row and a member file, re-tallies the votes, and lists any vote subjects the classifier couldn't categorize. It exits non-zero on any hard problems so it can gate the pipeline. 

## Analysis
`visualize_parliament.py` provides:
- **Cohesion metrics** : the Rice Index (|yea-nay|/(yea+nay)), and majority-share, per party per bill, with averages that exclude divisions a party did not vote in.
- **Dissent analysis** : because party discipline in the House of Commons tends to be strong (such that Rice scores saturate >= 99) the more informative statistics are *dissent frequency* (share of divisions with any 'rebel'), rebel counts per bill, and per-MP loyalty scores. 
- **The Whip Test** : `bill_info.py` classifies every division by business category (government bill, private members' bill, opposition motions, procedural supply, throne speech, committee report, appointment) plus reading stage and a confidence flag. `print_whip_report()` then cross-calculates dissent by category, and `mp_loyalty_split()` scores each MP seperately on whipped and free business. 

Example:
```
from visualize_parliament import print_whip_report, plot_dissent_by_category
print_whip_report("./Parliament_44-1")
plot_dissent_by_category("./Parliament_44-1")
```

## Experiments (roadmap)
1. **The Whip Test** : governing-party dissent on government bills vs. private members' business. 
2. **Twenty years of discipline** : cohesion and dissent frequency across all sessions; secular trend and minority-vs-majority parliaments.
3. **Government-status effect** : the same party's discipline in government vs opposition / government forming -> government transition.
4. **Where is the Rebel Base?!** : concentration of rebellion across MPs historically; conscience-caucus vs free-voters; do MPs who later leave a caucus rebel more beforehand?
5. **Confidence Gradient** : does dissent fall as the stakes of the vote category rise?
6. **Stage Effects** : dissent at second reading vs third reading of the same bills.
7. **Validation and Robustness** : Can we reproduce published unity scores, and re-run main results under corrections / adjustments to the cohesion / agreement calculation.

Per-session statistics exclude Parliament 40-1 (a single recorded vote before the 2008 prorogation). Dissent-rate analyses are run both with and without near-unanimous divisions as a robustness check.

## Longer-term ambitions

Extending to other voting bodies such as the UK House of Commons, and United States House of Represenatives and Senate. 

## Requirements
Python 3.10+ with 'requests' and 'matplotlib' (see 'requirements.txt').
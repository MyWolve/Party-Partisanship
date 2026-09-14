# Data you can use

Run `python analyze.py --group-by session --output outputs/all` for the full included snapshot, or use the README filters for a subset. Outputs are UTF-8 CSVs; blanks represent unavailable values, never zero. The compressed member file is an ordinary CSV after decompression.

| File | One row per | Important columns |
| --- | --- | --- |
| `divisions.csv` | Recorded division | `session`, `division`, `parliament`, `date`, `bill`, `bill_key`, `bill_type`, `category`, `stage`, `title`, `subject`, official `yeas`, `nays`, `paired`, `source_url`, `correction` |
| `members.csv.gz` | Observed member in a division | `session`, `division`, `member_id`, `member`, `raw_party`, analytic `party`, `vote`, `paired`, `binary_vote`, `correction` |
| `party_votes.csv` | Division × tracked party | Division metadata plus `party`, binary `yea`, `nay`, `whip_status`, `whip_scope` |
| `summary.csv` | Selected group × tracked party | Division and bill counts, dissent frequency/intensity and mean Rice, with their denominators |
| `manifest.json` | Analysis run | Selection, schema version, sessions and SHA256 hashes of selected input tables, correction records and code |

Join members to divisions on **(`session`, `division`)**. A member's ID is the stable person key; labels and party affiliation can change. Join bills on `bill_key` (session plus number). Empty bill keys indicate unnumbered business. Long titles come from archived LEGISinfo metadata; `subject` describes the vote and stage. `bill_type=Unknown` means no joined bill metadata, including non-bill business; it is not inferred from the category.

`vote` retains Yea/Nay dual coding; it counts on both sides of official tally checks. `paired` is True/False. `binary_vote` is blank for paired or dual-coded observations. No synthetic absence records are added. Minor affiliations map to Independent for analytic grouping while their available source labels remain in `raw_party`. One restored member has an unresolved original minor-group label, recorded as Independent in the correction record.

A nonempty `correction` links to a division-level entry in `audit/data_decisions.json`. It flags that the division required repair, not that every member in it was changed. Raw source files remain in the original session directories. Read `audit/DATA_DECISIONS.md` for the original and effective totals.

`selected_divisions` includes ties and no-vote party observations. `eligible_divisions` counts only defined party majorities. `dissenting_divisions` counts any minority vote. `eligible_member_votes` and `minority_member_votes` use that same majority-defined subset. `rice_divisions` includes ties but excludes no-vote observations. `bills` counts distinct nonempty session/bill keys; it is not the denominator of dissent frequency. No equal-bill weighting is implicit.

`whip_status` reports party/stage-specific documented free or unresolved cases, otherwise an explicitly labelled business-category proxy. `whip_scope` retains cabinet/backbench limitations. These labels do not establish an individual's instruction or beliefs. All statuses are included in the default summary.

Example with pandas (optional, not a project dependency):

```python
import pandas as pd
members = pd.read_csv('outputs/all/members.csv.gz')
divisions = pd.read_csv('outputs/all/divisions.csv')
votes = members.merge(divisions, on=['session', 'division'], validate='many_to_one')
postal = votes[votes['bill_key'] == '42-1/C-89']
```

In R: `read.csv(gzfile("outputs/all/members.csv.gz"))`. For spreadsheets, decompress first and filter the analysis to fit the application's row limit; the full member table exceeds one million rows.

The saved 45-1 session is incomplete. A new collection is a separate snapshot until reviewed. Comparisons use recorded participation and may differ in topics, caucus sizes, stages and session coverage. Cite the source URLs, commit and filters with any shared result.

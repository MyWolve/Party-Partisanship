# Data decisions

The original CSV and metadata files remain unchanged. The effective records are reconstructed at load time using checksum-bound decisions and frozen source evidence. These are data repairs, not a numerical tolerance for unexplained differences.

## Discrepancy inventory

| Session | Division | Raw Yea and Nay | Effective flag totals | Treatment |
| --- | --- | --- | --- | --- |
| 38-1 | [159](https://www.ourcommons.ca/members/en/votes/38/1/159) | 100 / 168 | 100 / 169 | Recover 1 dual-coded member(s) |
| 39-1 | [166](https://www.ourcommons.ca/members/en/votes/39/1/166) | 29 / 224 | 29 / 225 | Recover 1 dual-coded member(s) |
| 39-2 | [57](https://www.ourcommons.ca/members/en/votes/39/2/57) | 99 / 176 | 99 / 177 | Recover 1 dual-coded member(s) |
| 40-3 | [12](https://www.ourcommons.ca/members/en/votes/40/3/12) | 148 / 108 | 148 / 114 | Recover 6 dual-coded member(s) |
| 41-1 | [208](https://www.ourcommons.ca/members/en/votes/41/1/208) | 35 / 249 | 35 / 250 | Recover 1 dual-coded member(s) |
| 41-1 | [351](https://www.ourcommons.ca/members/en/votes/41/1/351) | 68 / 166 | 68 / 167 | Recover 1 dual-coded member(s) |
| 41-1 | [425](https://www.ourcommons.ca/members/en/votes/41/1/425) | 79 / 172 | 79 / 174 | Recover 2 dual-coded member(s) |
| 41-1 | [699](https://www.ourcommons.ca/members/en/votes/41/1/699) | 161 / 113 | 161 / 120 | Recover 7 dual-coded member(s) |
| 41-1 | [742](https://www.ourcommons.ca/members/en/votes/41/1/742) | 165 / 107 | 165 / 115 | Recover 8 dual-coded member(s) |
| 41-1 | [748](https://www.ourcommons.ca/members/en/votes/41/1/748) | 149 / 124 | 149 / 125 | Recover 1 dual-coded member(s) |
| 41-1 | [752](https://www.ourcommons.ca/members/en/votes/41/1/752) | 217 / 41 | 217 / 42 | Recover 1 dual-coded member(s) |
| 42-1 | [106](https://www.ourcommons.ca/members/en/votes/42/1/106) | 133 / 155 | 133 / 156 | Recover 1 dual-coded member(s) |
| 42-1 | [136](https://www.ourcommons.ca/members/en/votes/42/1/136) | 227 / 80 | 227 / 81 | Recover 1 dual-coded member(s) |
| 42-1 | [150](https://www.ourcommons.ca/members/en/votes/42/1/150) | 222 / 62 | 222 / 63 | Recover 1 dual-coded member(s) |
| 42-1 | [175](https://www.ourcommons.ca/members/en/votes/42/1/175) | 80 / 212 | 80 / 215 | Recover 3 dual-coded member(s) |
| 42-1 | [71](https://www.ourcommons.ca/members/en/votes/42/1/71) | 69 / 252 | 69 / 253 | Recover 1 dual-coded member(s) |
| 42-1 | [713](https://www.ourcommons.ca/members/en/votes/42/1/713) | 105 / 163 | 105 / 164 | Recover 1 dual-coded member(s) |
| 42-1 | [724](https://www.ourcommons.ca/members/en/votes/42/1/724) | 39 / 245 | 40 / 245 | restore member |
| 42-1 | [871](https://www.ourcommons.ca/members/en/votes/42/1/871) | 0 / 0 | 172 / 134 | restore division |

## Dual flags are not ordinary binary votes

The official XML explains all 17 dual-coded discrepancies: 38 member-divisions have both IsVoteYea and IsVoteNay set. The CSV retains only one side. These flags account exactly for the previously unexplained tally gaps, including gaps of six, seven, and eight. They are not generically described as votes struck after the division.

Both flags contribute to the official tally check. Neither side enters binary cohesion, dissent, or loyalty for that member-division. The parliamentary record is preserved rather than choosing a side. The original raw file, exact metadata row, official identities, flags, and source hashes are checked by the offline builder.

Paired-plus-binary combinations are a separate issue already visible in the raw CSV: they need no source repair, but the old loader incorrectly counted their Yea/Nay side. The new binary filter excludes any paired observation. All combination-coded exclusions, including these cases, are listed in the combination_votes_excluded field of [integrity.json](integrity.json). Ordinary paired-only rows are excluded as before.

## Division 871 restored from the Journals

The [June 19, 2018 Journals](https://www.ourcommons.ca/documentviewer/en/42-1/house/sitting-317/journals) list 172 Yeas and 134 Nays for division 871. The vote page and XML are empty. The builder extracts every Journal name and uniquely matches it against the official division 872 roster from the same sitting. This supplies identifiers and affiliations, not vote choices. Every vote choice comes from the division 871 Journal list.

The reconstructed 306-member record is [derived/42-1-871.csv](derived/42-1-871.csv). Metadata totals and the outcome are overridden explicitly. The same-sitting affiliation join assumes no intervening affiliation change; the source and join procedure are retained for inspection. No unmatched or ambiguous name is allowed.

## Missing member in division 724

The [June 5, 2018 Journals](https://www.ourcommons.ca/documentviewer/en/42-1/house/sitting-308/journals) list 40 Yeas and 245 Nays. The member export has 39 and 245. The absent member is Monique Pauzé, recorded as Yea. The reconstruction matches the full Journal list against the original XML plus her adjacent-day identity and confirms that every existing vote agrees.

The June 4 roster labels her Groupe parlementaire québécois and the June 6 roster labels her Québec debout. Both are aggregated as Independent by this project. The appended analytical row therefore uses Independent; the exact June 5 minor-group label remains unresolved and is not invented. This correction is not appropriate for a future study that distinguishes those minor groups without further affiliation research.

## Rebuilding and guarding the decisions

Run `python tools/build_audit_data.py --check`. It re-derives the registered JSON and reconstructed CSV from the frozen evidence, verifies all source checksums, and compares them with the saved products. Normal experiment runs call this guard before processing the corpus. A changed raw file, metadata row, derivation, or unexplained tally difference blocks analysis.

The [baseline inventory](baseline_discrepancies.json) records all 19 original problems. [data_decisions.json](data_decisions.json) records the exact operational decisions. [input_manifest.json](input_manifest.json) identifies the entire frozen input set. New evidence must be reviewed before deliberately registering a new snapshot.

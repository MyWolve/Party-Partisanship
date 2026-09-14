# Using the corrected voting dataset

Download this directory with the repository. `processed/members.csv.gz` and `processed/divisions.csv` contain the effective corpus used by the analysis, including the documented repairs. Reading these tables requires no project-specific loader. UTF-8 CSVs use a header row and LF line endings; decompress the member table with any gzip reader.

The package covers 13 sessions from 38-1 through the **incomplete 45-1 snapshot**, including the single division in 40-1. It contains observed voting/paired records, not a complete roster of seats or a matrix of all possible MP–division combinations. A missing person–division row does not establish absence, abstention or ineligibility. Session dates and record counts are in `processed/manifest.json`; those dates describe observations, not a guarantee of historical coverage.

## Files and joins

| File | Unit and purpose |
| --- | --- |
| `processed/members.csv.gz` | One observed person × session × division; corrected flags and analysis eligibility |
| `processed/divisions.csv` | One session × division; corrected metadata and project classifications |
| `processed/bill_sponsors.csv` | One session × bill; official sponsor Person ID, source labels, evidence and observed-vote linkage |
| `processed/repairs.json` | Repair ID → source-bound decision, original hashes, explanation and evidence paths |
| `processed/sources.json` | Evidence filename → source URL, retrieval date and byte hash |
| `processed/manifest.json` | Schema version, frozen corpus identifier, coverage and output-content hashes |

Join member and division tables on **both `session` and `division`**, many to one. Join `repair_id` to the keys in `repairs.json`; strip `evidence/` from its source paths to look up the ledger. The original records and evidence bytes remain in the repository. The ledger dates apply to archived review evidence, not retroactively to the original exports.

## Member dictionary

| Field | Type and meaning |
| --- | --- |
| `session` | Text, Parliament-session such as `42-1` |
| `division` | Positive integer; only unique within a session |
| `person_id` | Positive official Person ID, serialized as text; longitudinal identity key |
| `member` | Source display name at that division; not an identity key |
| `party_raw` | Affiliation retained from the source or documented repair; the Pauzé repair has a disclosed minor-group label assumption |
| `party_analytic` | Conservative, Liberal, NDP, Bloc Québécois, Green Party, or Independent; minor/unrecognized affiliations aggregate to Independent |
| `yea`, `nay`, `paired` | Integer flags, each 0 or 1; combinations are intentional, not mutually exclusive |
| `binary_vote` | `Yea` or `Nay` only for an unpaired single-sided vote; blank means excluded from binary metrics, not a zero vote |
| `repair_id` | `session/division` if this member record was reconstructed, appended or restored to dual coding; otherwise blank |
| `source_file` | Repository-relative original member CSV; repaired values can differ from that file |

Do not apply repairs again to this export. Sum `yea`, `nay` and `paired` separately to reproduce official tallies. Use `binary_vote` for cohesion or dissent: dual and paired combinations contribute to official flag totals but are excluded from those metrics.

## Division dictionary

| Field | Type and meaning |
| --- | --- |
| `session`, `division` | Composite primary key, as above |
| `date` | Source ISO date/time text, without an inferred timezone; sitting dates can differ from calendar dates after midnight |
| `subject`, `result` | Source subject and recorded decision result, with registered metadata repairs applied |
| `yeas`, `nays`, `paired` | Nonnegative integer official flag totals; a dual-coded person contributes to both sides |
| `bill` | Formatted bill number, sometimes recovered from subject; blank when unavailable. Use session + bill for grouping |
| `bill_type` | LEGISinfo type, or number-based inference where indicated; blank when unknown |
| `bill_type_source` | `legisinfo`, `number_inference`, or `unknown` |
| `category` | Project classification: government_bill, private_members_business, opposition_motion, government_motion, procedural, throne_speech, supply, appointment, committee_report, unknown_bill, or other |
| `stage` | second_reading, third_reading, report_stage, senate_amendments, amendment, or blank if unclassified |
| `confidence_proxy` | 0/1 keyword-based indicator; not an authoritative confidence designation |
| `repair_id` | Division-level repair reference if any decision applies, including member-only repairs; otherwise blank |
| `source_file` | Repository-relative original division metadata file |

The export does not give every MP a free/whipped label. Those historical instructions are party- and stage-specific, sometimes only cover backbenchers, and can remain unresolved. The generated [E1 classification table](../experiments/results_e1/classification_audit.csv) supplies party-level decisions and denominators; it excludes 40-1 and covers the five parties studied in E1.

## Bill sponsor dictionary

Join `bill_sponsors.csv` to division metadata on **session + bill**, not bill number alone. The table covers the frozen bill archive, including bills with no recorded division. Missing bill numbers in division metadata cannot be joined. Sponsor identities come from official sponsor-index IDs and the corresponding filtered bill lists; names do not assign IDs.

| Field | Meaning |
| --- | --- |
| `session`, `bill`, `bill_id` | Composite bill key and LEGISinfo numeric bill identifier |
| `sponsor_person_id` | Official Parliament Person ID; a text join key to `members.person_id` where that person has observations |
| `sponsor_name` | Source sponsor-index display label, usually surname first |
| `originating_chamber` | House or Senate, for the bill; not a person's lifetime chamber affiliation |
| `sponsor_index_aliases` | JSON list of index labels retained for the same ID; spacing variants do not create new people |
| `archived_sponsor` | Label preserved from the original historical XML; blank where that archive is absent |
| `archived_name_comparison` | normalized_agreement, different_label, or not_archived; a label comparison, never identity inference |
| `observed_in_session_votes` | True/False: this ID appears in the frozen session's observed House voting records; False is not proof of nonmembership |
| `identity_method` | official_sponsor_filter; source-count discrepancies and direct-detail corroboration are documented separately |
| `temporal_scope` | bill_record_at_retrieval; no effective dates or per-division sponsor history are asserted |
| `source_file`, `index_source` | Archived filtered membership response and sponsor index |
| `detail_source` | Archived per-bill JSON for the reviewed detail subset; blank outside that subset |

Senate sponsors need not appear in the House voting data. Do not confuse a Person ID with the distinct `SponsorSenateSystemAffiliationId` in detailed source responses. A bill-level sponsor is not automatically its mover on every division, a later-stage sponsor in the other chamber, or its sponsor on an arbitrary historical date. Original and retrieval-time labels remain separate. [Sponsor recovery review](../audit/SPONSOR_RECOVERY_REVIEW.md)

## Read without this project's code

```python
import csv
import gzip

with open('data/processed/divisions.csv', encoding='utf-8', newline='') as f:
    divisions = {(r['session'], r['division']): r for r in csv.DictReader(f)}

with gzip.open('data/processed/members.csv.gz', 'rt', encoding='utf-8', newline='') as f:
    for member in csv.DictReader(f):
        division = divisions[member['session'], member['division']]
        # member['binary_vote'] is blank for excluded combinations.
```

CSV readers return text: convert flags/counts explicitly. Spreadsheet software may coerce session IDs or truncate the member table; use a CSV-capable analysis tool for the complete dataset.

## Versions, verification and citation

Schema version 2 adds the bill-sponsor table to version 1's unchanged member/division fields. `snapshot_id` derives from the frozen input hash; it is not a software release number. Cite the full corpus hash **and Git commit**, since the same inputs can produce different outputs after code changes. The manifest lists SHA256 hashes of UTF-8 LF content; decompress gzip before hashing. Compression bytes may differ across zlib versions while the CSV content remains identical. Sponsor evidence is archived as gzip with separate hashes for the stored file and original response content, as declared in `sources.json`.

`python reproduce.py --check --repeat` rebuilds and checks this package along with E1/E7, including an independent CSV read-back that checks official tallies and E1's party denominators/minority counts. To generate a separate copy, run `python tools/export_dataset.py --output-dir incoming/export-review` with a new directory. A direct export checks frozen inputs and corpus integrity; the full reproduction command additionally runs reconciliation, source coverage, tests and experiments. A failed direct export may leave a partial directory; only a completed manifest records success.

Suggested citation: **MyWolve. Party Partisanship: corrected Canadian House of Commons voting snapshot. Repository URL, Git commit, full corpus SHA256, and access date.** Also credit the underlying House of Commons and LEGISinfo records. For the E7 comparison deposit, retain the citation supplied by its authors: Godbout, Jean-François and Bjørn Høyland (2017), *Canadian Parliament Voting Data, 1867–2015*.

The repository has no selected project-wide license. This documentation supplies attribution and provenance, not a new license or a claim that all upstream material has identical reuse terms. Choosing a license for project-authored code and documentation remains an owner decision; source material retains its own terms.

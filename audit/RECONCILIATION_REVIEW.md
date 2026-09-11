# Record-level reconciliation and bill refresh review

## Outcome

The next two open engineering problems now have executable workflows: member-by-division reconciliation for Parliaments 38–40, and a separate LEGISinfo collection/comparison tool. No original parliamentary export, bill archive, or deposited matrix has been replaced.

## Record-level comparison

| Parliament | Divisions | Joined observable records | Exact vote-flag and analytic-party matches | Deposit-only observations |
| --- | ---: | ---: | ---: | ---: |
| 38 | 190 | 54,220 | 54,220 | 0 |
| 39 | 380 | 101,643 | 101,643 | 0 |
| 40 | 363 | 100,813 | 100,813 | 1 |
| Total | 933 | 256,676 | 256,676 | 1 |

Observable includes paired and combination-coded records, not just binary Yea/Nay. All 256,676 joined observations match in the underlying vote and paired flags and in the project's analytic party grouping. There are no official-only observations. Nonvoting/not-sitting cells (deposit codes 9 and 99) have no equivalent explicit rows in the official CSVs and are outside this identity claim. Speaker Peter Milliken has one unmatched, entirely nonvoting term per parliament; these three rows are listed and never converted into votes.

The [member crosswalk](reconciliation/member_crosswalk.csv) uses normalized names and constituencies within each parliament. Exact full names are preferred; constituency disambiguates names such as David Anderson; unique first-name/surname matches handle middle names. No vote pattern is used to choose an identity. Ambiguous or missing observable matches fail the command. This is an inspectable inferred crosswalk, not an official mapping between the deposit's historical IDs and current Person IDs. Party comparisons use the established analytic groups; minor-party label identity is not asserted.

The [division table](reconciliation/division_dates.csv) matches all 933 division identifiers and reports both dates. The [difference table](reconciliation/differences.csv) retains the single discrepant observation. Ordinary reproduction rebuilds and compares these products; changes require review rather than automatic acceptance.

### Volpe on 40-2/157

The deposit codes Joe/Joseph Volpe (Person ID 608) as Yea on December 10, 2009, division 157. The frozen official CSV omits him. A newly retrieved [official XML](../evidence/40-2-157.xml) also omits him, and the [Journals of sitting 128](https://www.ourcommons.ca/documentviewer/en/40-2/house/sitting-128/journals) list 142 Yeas and 143 Nays without Volpe in this division. The [archived Journals](../evidence/40-2-157-journals.html) preserve that evidence.

Decision: retain the official corpus and preserve the comparison deposit unchanged. The records disagree, and the official evidence supports retaining the current omission. No claim is made about the cause of the deposit's extra vote. All 36 rounded aggregate benchmark values still match; that result alone could not reveal this discrepancy.

### Date on 38-1/153

The deposit dates this division June 27, 2005; the export timestamp is June 28 at 00:00. The [Journals for the June 27 sitting](https://www.ourcommons.ca/documentviewer/en/38-1/house/sitting-123/journals) include division 153 and record adjournment at 12:22 a.m. The [archived source](../evidence/38-1-153-journals.html) supports a sitting-date versus calendar-date explanation. All member flags and analytic affiliations match for the division. Both source dates are preserved. Future calendar-based analysis must choose and state a date convention.

## Bill refresh

The current LEGISinfo XML uses `NumberCode`, `BillDocumentTypeNameEn`, and `SponsorPersonName`; the frozen archive uses `BillNumberFormatted`, `BillTypeEn`, and `SponsorEn`. The previous loader would silently return no bills for the new schema, leaving downstream classification to numbering inference.

`bill_data.py` now supports both explicit schemas and rejects unknown/ambiguous schemas, duplicate fields or bill numbers, wrong sessions, missing titles, and unknown bill types. Split bills such as C-23A remain valid. This parser is shared by the analytical loader and refresh tool.

The live 40-1 check retrieved 77 bills. All 77 bill numbers, types and titles match the frozen archive, but **all 77 sponsor names are blank in the new export**. The [field comparison](bill_refresh_changes.json), [retrieval receipt](bill_refresh_receipt.json), and [new raw XML](../evidence/legisinfo-40-1-current.xml) preserve the result. No sponsor name is guessed or copied into the new raw snapshot. The tool flags lost sponsor fields for review.

Decision: do not replace the frozen archive with this response. The separate snapshot workflow is implemented; promotion remains a deliberate reviewed operation. Historical sponsor recovery and checking later-session coverage remain open source questions. A schema-valid download is not necessarily an improvement over the archive.

## Commands and validation

```text
python tools/reconcile_members.py --check
python tools/collect_bills.py --session 40-1 --output incoming/bill-review-new
python tools/collect_bills.py --session 40-1 --source-xml evidence/legisinfo-40-1-current.xml --output incoming/bill-review-offline-new
python reproduce.py --check --repeat
```

Both collection commands require a new directory. They preserve the raw response and a failed manifest if validation fails. Reconciliation uses the frozen inputs without network access. The expanded suite contains 50 tests, including real record-level expectations, same-name disambiguation, renamed/split bills, schema migration, and overwrite/failure protection. Full reproduction also compares the saved reconciliation products.

The input manifest was deliberately extended with four supporting source snapshots and the updated source ledger. The original parliamentary/deposit data is unchanged; its analytical results are unchanged. E7's explanation now links this record-level evidence. The latest run manifest and PR checks identify tested code and platform outcomes.

## Next open work

- Historical whip designations and the exact minor-group label already listed in the source audits.
- Independent verification of later parliaments beyond the deposited 38–40 comparison window.
- Establishing complete, nondegrading bill refresh coverage across sessions, including missing historical sponsors.
- Methodological extensions such as bill-level weighting and caucus-size effects after source review.

This closes the absence of a reconciliation product and a reviewed refresh mechanism. It does not erase documented source disagreements or claim that every later parliamentary record has independent corroboration.

Update: the [source coverage review](SOURCE_COVERAGE_REVIEW.md) extends bill comparisons across all sessions and checks a fixed later-session XML sample. It closes the missing 45-1 type archive using a reviewed supplement; widespread missing sponsor fields and independent later-session corroboration remain open.

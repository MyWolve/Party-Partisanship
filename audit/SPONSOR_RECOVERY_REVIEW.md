# Bill sponsor recovery and Person ID linkage

## Outcome

The recovered table covers **all 4,596 bills in the 13-session frozen bill universe**: 4,411 historical bills plus 185 in the 45-1 supplement. Each bill has exactly one official sponsor association, representing **783 distinct Person IDs**. No identifier was assigned by matching names.

The reusable [bill sponsor table](../data/processed/bill_sponsors.csv) joins to division metadata on session + bill and to observed member records on Person ID. It includes 3,967 House-originating and 629 Senate-originating bills. For 3,958 House bills, the sponsor ID appears in the session's observed House votes. Nine House bills have sponsors without an observation in the one-division 40-1 session; they are retained, not treated as missing identities. All 629 Senate bills retain their sponsors even though those IDs have no House voting observation in the corresponding session.

This recovers bill-level sponsor identity. It does not reconstruct dated changes of sponsor, movers of individual motions, or sponsorship in the other chamber. `temporal_scope=bill_record_at_retrieval` makes that boundary explicit.

## Source route and checks

The session-wide LEGISinfo XML and JSON exports omit sponsor names and IDs. The official per-bill JSON still supplies `SponsorPersonId` and `SponsorPersonName`. The sponsor index and sponsor-filtered bill lists also retain the association. For example, the [40-1/C-2 detailed export](https://www.parl.ca/legisinfo/en/bill/40-1/c-2/json) identifies Stockwell Day as Person ID 1792. `SponsorSenateSystemAffiliationId` is a separate identifier and is never substituted for Person ID.

The bulk recovery archives 13 session indexes and 783 sponsor-filtered lists. Each response has its requested/resolved URL, retrieval date, response SHA256 and stored gzip SHA256 in [the evidence ledger](../evidence/sources.json). Gzip compression preserves the original response after decompression. Archived files are verified and never overwritten during retrieval.

Offline reconstruction checks bill/session uniqueness, types and titles against the frozen bill universe, sponsor-index identities, filtered membership, and complete one-sponsor coverage. JSON title text is normalized only for XML's newline conversion and the existing adapter's outer trimming: nine raw titles differ in CRLF or trailing whitespace, with no substantive title difference. This does not authorize fuzzy title matching.

**113 direct bill-detail responses** corroborate the filtered IDs and bill IDs. The deterministic selection includes the first lexicographically sorted bill in each session/originating-chamber group, all 77 bills in 40-1, every archived-label discrepancy, and every bill in the six count-exception pairs below. These are two interfaces from the same publisher, not independent historical sources.

## Preserved source discrepancies

Six published sponsor-index counts exceed their actual filtered results. Session-specific exports reproduce the same results as the all-session filter. Full membership nevertheless covers the frozen bill universe exactly once. The cause of the interface overcounts is not established.

| Session | Person ID | Sponsor | Index count | Filtered bills |
| --- | --- | --- | --- | --- |
| 38-1 | 212 | Richard Marceau | 4 | 2 |
| 38-1 | 218 | Gérard Asselin | 5 | 1 |
| 39-1 | 259 | Réal Ménard | 20 | 1 |
| 39-2 | 259 | Réal Ménard | 19 | 1 |
| 40-2 | 218 | Gérard Asselin | 5 | 1 |
| 40-3 | 218 | Gérard Asselin | 3 | 1 |

The [index comparison](sponsors/index_counts.csv) retains all 1,938 sponsor/session count rows. Only these exact six discrepancies are allowed; a new difference stops reconstruction. The affected bills also receive direct-detail corroboration. No count is silently adjusted to make the interfaces agree.

In 44-1, the index splits Person ID 88605 into `Fortin, Rhéal Éloi` and `Fortin, RhéalÉloi`, each with one bill. Both labels are preserved, and their sum agrees with the two filtered bills. Identical duplicate entries or conflicting names fail validation.

Of the 4,411 archived sponsor labels, 4,394 agree under conservative name-format normalization. Sixteen further differences are `Right Hon.` honorific formatting. The remaining case is 42-1/C-419: archived `Rachael Thomas`, indexed `Harder, Rachael`, and direct-detail `Rachael Harder`, all linked to Person ID 89200 by the official association. Both source labels remain available; this review does not infer when a name or source label changed.

## Collection, export and reproducibility

```text
python tools/collect_bills.py --session 40-1 --output incoming/new-sponsor-review --with-sponsors
python tools/recover_sponsors.py --check
python reproduce.py --check --repeat
```

The optional `--with-sponsors` collector retrieves per-bill JSON, validates identity/session/type/title, records response provenance and writes `bill_sponsors.json` beside the raw XML. Its separate live test completed for all 77 bills in 40-1 with no missing sponsor fields; all 77 IDs agree with the filtered mapping. Thirty displayed sponsor labels differ from the older XML, illustrating why raw labels and IDs are separate. Errors retain downloaded detail responses and a failed collection manifest. The original archives are not replaced.

`tools/recover_sponsors.py --fetch` explicitly collects missing evidence; normal recovery and reproduction are offline. The approved evidence expansion changes the input snapshot hash to `18f61060bc81242bcf92a55b0538e6ac281193f845ef2eb57703e2258f9a8135`. Original parliamentary CSVs and historical bill XMLs remain intact. The export schema advances to version 2 by adding a sponsor table; existing member/division fields are unchanged.

The test suite contains 69 tests, including detailed identity failures, namespace separation, collection failure retention, index ambiguities, and JSON/XML title normalization. Full reproduction rebuilds the sponsor mapping and count report, packages the table, and checks sponsor coverage for official bill lookups in the exported divisions. E1/E7 do not use sponsorship in their calculations; this addition supplies evidence for future sponsor-level questions without revising their research definitions.

The local `python reproduce.py --check --repeat` run passed, with table-content digest `9ee13d629f4a474feae84c23bcd725ed7aabf3b1a938107c76ac00d0d3dd122b`. All E1/E7 output files and the existing member/division/repair exports are unchanged. Comparing input manifests confirms that only the evidence ledger changed among existing inputs, with 915 sponsor evidence files added. The reconciliation summary changes only its corpus hash. The run manifest and PR CI report the exact code/environment and platform results.

Broader independent later-session verification, unresolved whip instructions, further experiments and the project license choice remain open. Sponsor histories with effective dates would require separate evidence before historical role or party attribution at individual votes.

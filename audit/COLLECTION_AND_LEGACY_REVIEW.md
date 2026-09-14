# Collection and legacy analysis review

This follow-up to the initial implementation audit reviews the collection and diagnostic entry points. The original frozen corpus is unchanged. Changes are on the same review branch and draft PR; main has not been merged.

## Findings and repairs

| Finding | Repair | Verification |
| --- | --- | --- |
| Collector overwrote metadata while keeping existing member files; transport failures were counted with skipped files | Replace implicit in-place updates with an explicitly named, new snapshot directory; propagate errors; retain failed status and received evidence | Tests for overwrite refusal, failed requests, header-only/HTML/mismatched data, and interrupted completeness |
| Loose XML substring matching could accept ambiguous metadata | Exact namespace-insensitive tag aliases; positive unique division numbers; required dates, subjects, results and nonnegative totals | Malformed, duplicate, empty and ambiguous metadata fixtures |
| Session could change during a collection | Fetch metadata before and after all member files; require the parsed records to match | Changing-session fixture fails; before/after responses retained |
| No retrieval provenance for raw collection | Record requested/resolved URL, UTC receipt time, HTTP status, content type, size and SHA256 for every received response | Successful fixture and live 40-1 collection |
| Single-division lookup used substring matching; random selection could choose metadata | Exact division names; restrict random helper to member files; command requires explicit session/output | file_1 versus file_10 fixture; reject metadata and path fragments |
| Plot command required a graphical desktop | Use Agg for command-line file generation | All six legacy chart families executed on 38-1 |
| MP tracking used display names, including changing constituency labels | E7 and legacy loyalty reports now group by Person ID, with latest observed names used for display | Renamed-member and floor-crossing fixtures; corpus scan found no missing Person IDs |
| Metadata loader did not reject duplicate/missing headers | Require unique headers and all eight contracted fields | Header-only failure fixtures |
| Missing category cells were plotted as zero dissent | Undefined observations plot as gaps | Plot implementation inspection and category-chart smoke run |
| Reproduction only demonstrated on local Windows | Add immutable-pinned GitHub Actions matrix for Windows/macOS Python 3.12.10 and Ubuntu Python 3.12.14 | Each job executes the same full reproduction command and uploads its environment/log evidence |

## Numerical consequences

Using stable Person IDs changes qualifying MP–party record counts: Parliament 41 Conservative 175 to 173; Parliament 42 Liberal 191 to 190; Parliament 44 Bloc 34 to 33. The displayed loyalty values are unchanged at two decimals. All 36 deposited-data benchmark comparisons still match exactly. E1 counts, rates, classifications and findings are unchanged. This is an identity correction, not a new analytical specification.

Legacy report mappings now use Person ID keys; split-loyalty records include a `member` display label. Callers using these exploratory Python functions must account for that API change. The pure `mp_loyalty(bills)` helper uses the identities supplied by its caller; use `load_member_history` for stable-ID histories. `load_parliament` keeps human-readable default labels for single-division exploration and exposes `member_ids=True` for longitudinal work.

## Collection check

A live 40-1 collection completed into ignored `incoming/40-1-collection-review`, validating its one division and matching start/end metadata. No live data was copied into the analysis corpus. This verifies the collector's live request path on a small historical session, not every session or failure mode. The failure-path fixtures exercise those behaviors offline.

Raw CSV inconsistencies still cause collection failure. The collector does not silently apply the analytical corpus's repair overlays to a new download. A failed snapshot requires source review. Successful collection establishes internal coverage and tally agreement; it does not establish historical truth or completeness of the publisher's own list. Before/after checks detect changed metadata, not a publisher's unannounced member-level edit that leaves totals and metadata unchanged.

## Verification register and remaining work

Completed in this pass: collection lifecycle, schema failures, identity handling, deterministic legacy command selection, headless plotting, metadata headers, and CI configuration. The regression suite now contains 41 tests. Local reproduction is rerun after the final changes; exact evidence is in `run_manifest.json` and `validation_log.txt`. GitHub job outcomes must be read from the PR checks; a configured workflow alone is not proof of cross-platform success.

The following research/engineering items remain explicitly open:

- Member-by-division reconciliation against the comparison deposit. Aggregate agreement is not record identity; matching vote identifiers, affiliations and missingness requires a dedicated comparison product.
- Recovering historical whip instructions and exact minor-party labels for the unresolved cases listed in the classification/data audits.
- A reviewed LEGISinfo refresh workflow. Existing XML is frozen and hashed; the new collector collects vote metadata/member exports, not an updated bill archive.
- Independent source verification across the entire corpus, beyond the discrepancy-driven repairs and publisher tally checks.
- Bill-level weighting, caucus-size effects and later experiments. These are methodological changes and should follow the collection and validation review.

The old `scrape_all()` and implicit in-place scraper interfaces have been removed deliberately. Use the explicit collection command in REPRODUCING.md. This branch remains a review package; no merge or wholesale live refresh is performed.

The first CI run exposed unavailable Python 3.12.14 builds on Windows/macOS. GitHub's official versions manifest provides 3.12.10 for those platforms; the matrix now pins those available builds and retains 3.12.14 on Ubuntu. The local reference uses bundled Windows 3.12.14. No analytical tolerance or dependency was changed to address the setup failure.

Update: [the next review](RECONCILIATION_REVIEW.md) implements the member-level comparison and bill-refresh mechanism. It resolves the comparison window to one documented observation difference and one date-convention difference, and identifies missing historical sponsors in a live bill export. The remaining source questions are listed there.

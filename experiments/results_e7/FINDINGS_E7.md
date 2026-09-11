# E7 Aggregate data agreement

All 36 comparisons pass the 1.00-point criterion. 36 match to two decimals; the maximum absolute difference is 0.00 percentage points.

The benchmark values are computed from Godbout and Høyland’s deposited raw matrices, using shared definitions. This is an aggregate data-agreement check for Parliaments 38–40, not an independent validation of the arithmetic, the vote classifier, or later parliaments. Hand-calculated regression fixtures provide a separate check of metric behavior.

The reviewed baseline had 27 exact matches, not the previously documented 30. Member-level reconciliation now matches 256,676 observable records exactly in vote flags and analytic party across 933 divisions. One additional Yea in the deposit (Volpe, 40-2/157) is absent from the official export and Journals. A midnight sitting-date difference is documented separately. See the [record-level audit](../../audit/RECONCILIATION_REVIEW.md); aggregate agreement does not establish complete record identity.

Contested means more than five observable binary votes on each side of the House. MP loyalty averages require at least 25 qualifying votes and omit tied party divisions. Paired and dual-coded member-votes are omitted. Two-member caucus loyalty is degenerate because splits have no majority. The small-group series is a nonnegative baseline adjustment; it excludes singleton votes and should not be presented as a fully replicated published estimator.

See [all comparisons](benchmark_comparison.csv), [unity table](unity_by_parliament.csv), [validation summary](validation_summary.json), and [reproduction instructions](../../REPRODUCING.md).

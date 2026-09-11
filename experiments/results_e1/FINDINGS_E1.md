# E1 Dissent by parliamentary business

Government bills: **41/1491** divisions with governing-party dissent (2.75%). Private members’ business: **225/848** (26.53%). The descriptive ratio is **9.65**.

Supply: **1/1118**. The main comparison excludes 22 documented free stages for the governing party. There are 10 governing-party divisions with explicitly unresolved status; see sensitivity below.

## Sensitivity

| Scope | Government dissent | Private business dissent | Ratio |
| --- | --- | --- | --- |
| category only | 61/1513 | 225/848 | 6.58 |
| documented free excluded | 41/1491 | 225/848 | 9.65 |
| uncertain excluded | 32/1482 | 225/848 | 12.29 |
| unknown bill as government | 41/1492 | 225/848 | 9.66 |

Category only retains documented free stages. The main comparison removes them. Uncertain excluded additionally removes audited unresolved cases; it does not imply that the remainder has verified whip instructions. Unknown bill as government tests the malformed bill subject separately. The CSV also contains contested-only versions (no more than 95% of observed binary House votes on either side).

## Repeated bills and participating caucus size

| Category | All divisions | Numbered-bill divisions | Equal bill mean | Session–bill units | Unnumbered divisions omitted from bill check |
| --- | --- | --- | --- | --- | --- |
| government_bill | 2.75% | 2.75% | 5.15% | 281 | 0 |
| private_members_business | 26.53% | 29.41% | 32.71% | 467 | 185 |

The equal-bill mean first computes each session–bill’s fraction of eligible divisions containing dissent, then weights those bills equally. It is not the fraction of bills with any dissent. Bill numbers restart across sessions; the key includes session. The numbered-only division rate separates selection changes from weighting changes. Private members’ motions without a bill number remain in the headline but cannot enter this bill-level comparison. Reintroduced bills can still be related across sessions; no independence or causal claim follows.

| Category | Observed party voters | Divisions | Divisions with dissent | Minority member-votes |
| --- | --- | --- | --- | --- |
| government_bill | all | 1491 | 2.75% | 0.06% |
| government_bill | 1-100 | 3 | 0.00% | 0.00% |
| government_bill | 101-150 | 919 | 2.29% | 0.08% |
| government_bill | 151+ | 569 | 3.51% | 0.04% |
| private_members_business | all | 848 | 26.53% | 1.74% |
| private_members_business | 1-100 | 5 | 60.00% | 8.07% |
| private_members_business | 101-150 | 544 | 28.68% | 1.65% |
| private_members_business | 151+ | 299 | 22.07% | 1.82% |

Size bands count observed unpaired binary voters in the governing party, not seats or the full caucus roster. Bands (1–100, 101–150, 151+) are descriptive; they do not adjust for session, issue, attendance or bill composition. The minority member-vote rate divides minority votes by all eligible binary member-votes, so it measures intensity and weights larger participating groups more heavily. Tied majorities and documented free stages are excluded throughout. These are diagnostics of denominator choices, not an estimated effect of caucus size. Inspect [bill units](bill_units.csv), [weighting](design_checks.csv), and [participation](participation_checks.csv).

## Interpretation and limits

These are descriptive associations between business types and caucus voting patterns. They do not isolate the effect of whip enforcement. Issues, participating MPs, caucus size, repeated divisions on the same bill, and party policy can all differ across categories. One dissenter and many dissenters count equally. Tied caucus divisions have no majority and are excluded from this outcome. Paired and dual-coded member-votes are omitted from binary analysis. No uncertainty interval assuming independent divisions is asserted.

C-38 and C-14 designations are party- and stage-specific. Liberal designations cover backbenchers, not cabinet; the exclusion applies at the caucus-division level and is not an MP-level freedom label. C-30, C-17, recommittal, and C-14 Senate-amendment coverage remain unresolved where listed. Business category and confidence keywords are proxies. The observed government-bill rate is not asserted to be an upper bound on true whipped dissent.

See [classification audit](classification_audit.csv), [outliers and names](outliers.csv), [all counts](summary.csv), [sensitivity](sensitivity.csv), [source decisions](../../audit/whip_designations.json), and [reproduction instructions](../../REPRODUCING.md).

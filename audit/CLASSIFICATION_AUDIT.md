# Classification audit

The audit separates business category, evidence about whip instructions, and the population covered by those instructions. A government bill is not automatically a verified whipped vote. The decision records in [whip_designations.json](whip_designations.json) are the machine-readable source of the current rules.

## Verified scope

| Session and bill | Party | Documented population | Implemented coverage |
| --- | --- | --- | --- |
| 38-1 C-38 | Liberal | Backbenchers; cabinet constraint retained | Second reading, report stage, third reading |
| 38-1 C-38 | Conservative | Whole caucus | Second reading, report stage, third reading |
| 42-1 C-14 | Liberal | Backbenchers; cabinet excluded | Second reading, report stage, third reading |
| 42-1 C-14 | Conservative, NDP, Bloc | Whole caucus | Second reading, report stage, third reading |

For C-38, the [April 4 Hansard](https://www.ourcommons.ca/documentviewer/en/38-1/house/sitting-75/hansard) describes Liberal backbench freedom and the cabinet constraint. The [April 19 debate](https://www.ourcommons.ca/documentviewer/en/38-1/house/sitting-85/hansard) and [June 22 debate](https://www.ourcommons.ca/documentviewer/en/38-1/house/sitting-121/hansard) support the Conservative free-vote policy and discussion of the cabinet limitation during the later debate.

For C-14, the Library of Parliament's [Party Discipline and Free Votes](https://www.publications.gc.ca/collections/collection_2019/bdp-lop/eb/YM32-5-2018-26-eng.pdf), section 5, records the party scopes and Liberal cabinet exception. The [June 6 Hansard](https://www.ourcommons.ca/documentviewer/en/42-1/house/sitting-66/hansard) discusses the Liberal free vote. Later in the same sitting, Peter Julian disputes the Prime Minister's assertion that the NDP vote was whipped; the Library account also describes it as free. [Elizabeth May's report-stage speech](https://elizabethmaymp.ca/report-stage-speech-on-c-14/) supplies direct contemporaneous discussion of free voting at report stage.

The rules apply these documented bill policies to substantive readings and report stage. They do not assert that the sources enumerate every amendment. Recommittal, Senate-amendment scope, and procedural motions are not automatically covered. This is a conservative operationalization, and the category-only sensitivity retains all substantive divisions regardless of designation.

A Liberal backbench designation causes a caucus-division to be excluded from the main government-bill comparison. It does not label every participating Liberal MP as free, infer who was in cabinet, or create a backbencher-only estimate. The classification output retains `member_scope` to make that distinction visible.

## Unresolved questions

**C-30 in 38-1.** The [December 9 debate](https://www.ourcommons.ca/documentviewer/en/38-1/house/sitting-42/hansard) and [March 23 debate](https://www.ourcommons.ca/documentviewer/en/38-1/house/sitting-73/hansard) identify the pay legislation and objections to its framework. They do not establish the required Liberal whip instructions. The case remains unresolved. Dissenter counts alone cannot resolve it.

**C-17 in 38-1.** Searches for an explicit designation did not establish the instructions on the committee-referral division. The [bill identifier](https://www.parl.ca/legisinfo/en/bill/38-1/c-17) anchors the case to the correct parliament; superficially similar references to C-17 in other sessions were not accepted as evidence.

**Later and procedural stages.** C-38 recommittal and C-14 recommittal and Senate-amendment votes remain unresolved under these rules. Procedural motions retain a business-category proxy and do not inherit a free-vote designation merely by mentioning a bill number.

**Malformed subject.** Session 42-1 division 247 names a bill but omits its number. It is now `unknown_bill`. The MVP retains that unknown category. No data is discarded to conceal the uncertainty.

## Use in the MVP

The links above document the party- and stage-specific designations. The MVP exports them in `party_votes.csv` for inspection. All matching divisions, including documented free stages, enter the default descriptive summary. Categories and dissent do not establish whip instructions or personal motives.

Repair evidence is limited to official records required for the tally corrections, plus the 45-1 bill metadata supplement. The broader source-archiving and research work remains on `codex/reproducibility-audit`.

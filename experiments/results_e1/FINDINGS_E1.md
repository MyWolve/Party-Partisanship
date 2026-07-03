# E1 — The Whip Test: Findings

*Experiment run: July 2026, on the full verified corpus (sessions 38-1
through 45-1, ~4,850 divisions). Script: `experiments/experiment_e1.py`;
classification: `bill_info.py` with the C-38 designated-free-vote override
active. Parliament 40-1 excluded (one recorded division). 45-1 was in
progress at time of analysis.*

## Question

Are Whips that successful? (README, original question 3.)

## Method

For each session, compare the **governing party's** dissent rate (share of
divisions with at least one member voting against the party majority) on
**government bills** — whipped by convention — against **private members'
business** — traditionally free. Same caucus, same parliament, whip on
vs. whip off, controlling for party culture. Divisions on documented
designated free votes (currently the Civil Marriage Act, C-38, 38-1) are
excluded from the whipped column. A robustness variant excludes
near-unanimous divisions (>95% of the whole House on one side); it does
not change any conclusion and is omitted from the tables below (full
numbers in `results_e1/summary.csv`).

## Headline result

Pooled across all governments, 2004–2026:

| business                     | divisions with dissent | rate  |
|------------------------------|------------------------|-------|
| Government bills (whipped)   | 50 / 1,502             | 3.3%  |
| Private members' business    | 225 / 848              | 26.5% |

**When the whip comes off, the same MPs dissent 8.0× more often.**
Confidence-adjacent business is stricter still: governing parties dissented
on **1 of 1,118 supply divisions (0.09%)** across the whole corpus.

## Per-session results (governing party)

| session | government   | whipped % | free %  | note                        |
|---------|--------------|-----------|---------|-----------------------------|
| 38-1    | Liberal      | 13.6      | 71.8    | 11 C-38 divisions excluded  |
| 39-1    | Conservative | 1.4       | 38.1    |                             |
| 39-2    | Conservative | 2.4       | 10.4    |                             |
| 40-2    | Conservative | 0.0       | 17.0    |                             |
| 40-3    | Conservative | 0.0       | 20.8    |                             |
| 41-1    | Conservative | 0.0       | 22.3    |                             |
| 41-2    | Conservative | 0.0       | 27.0    |                             |
| 42-1    | Liberal      | 6.4       | 26.1    | C-14 override pending       |
| 43-1    | Liberal      | 0.0       | —       | no PMB divisions (COVID)    |
| 43-2    | Liberal      | 13.6      | 34.8    |                             |
| 44-1    | Liberal      | 3.2       | 24.3    |                             |
| 45-1    | Liberal      | 8.3       | 8.7     | small n; session in progress|

## Findings

1. **The Harper whip was near-perfect.** Conservative governments
   dissented on 2 of 762 government-bill divisions across seven sessions
   (0.26%), including an unbroken run of **646 consecutive government-bill
   divisions with zero dissenting Conservative votes** (40-2 through 41-2,
   roughly 2009–2015). The same caucus dissented on 10–27% of private
   members' business in those sessions.

2. **Liberal and Conservative governments whip differently.** Liberal
   governments (42-1 onward) show 5.9% government-bill dissent — roughly
   twenty-fold looser than Harper-era Conservatives — consistent with the
   2015 Liberal platform commitment to free backbench votes outside
   confidence, charter, and platform matters. Neither party's government
   tolerates dissent on supply.

3. **The Martin minority (38-1) is the loosest government in the corpus**
   even after excluding its designated free votes: 13.6% whipped dissent,
   71.8% free — both corpus highs.

4. **45-1 (Carney) is an early anomaly**: the only session with no
   whipped/free gap (8.3% vs 8.7%). Small denominators (60 and 23
   divisions); flag for re-examination as the session matures, in E2.

## Outlier audit (largest governing-party rebellions on government bills)

The spot-check list served its purpose twice over: in the first run it
exposed a classification bug (a curly apostrophe in LEGISinfo's
"Private Member's Bill" misfiled all PMBs as government bills), and in the
corrected run it recovered known history:

- **C-38 (38-1), Civil Marriage Act** — six of the original top ten; 34–35
  Liberal rebels at second reading matching the recorded dissent on the
  declared free vote (backbench free, cabinet whipped). Now excluded via
  `FREE_VOTE_BILLS`.
- **C-30 (38-1), MP compensation** — top of the corrected list (11–14
  rebels across three stages). Identified: the 2005 bill delinking MP
  salaries from judicial raises; debate records show Liberal members
  objecting to abandoning the independent (Lumley) process. Free-vote
  status unconfirmed — either a designated free vote on House matters or
  a genuine 14-member pay revolt. **TODO: check Journals/contemporary
  coverage before adding to overrides.**
- **C-14 (42-1), medical assistance in dying** — 5–7 rebels across three
  divisions; consistent with reported freeing of Liberal backbenchers
  (cabinet whipped). **TODO: verify, then add to `FREE_VOTE_BILLS`.**
- **C-89 (42-1), postal back-to-work legislation** — 5–6 Liberal rebels at
  second and third reading on emergency whipped business with no known
  free-vote designation. **Candidate for the corpus's first verified
  genuine rebellion on whipped government business.** TODO: pull rebel
  names (`find_rebels`, divisions 948/950) and check against the caucus's
  labour-aligned members.
- **C-17 (38-1), cannabis decriminalization** — 6 rebels;
  conscience-flavoured, free-vote status unverified. TODO.

## Caveats

- **Category is a proxy for whip status.** Designated free votes on
  government bills are handled via documented overrides only; undetected
  cases bias the whipped rate upward, so 3.3% is an upper bound on true
  whipped-business dissent.
- **Opposition-party PMB dissent is partly definitional**: with no whip
  line on free votes, deviation from the party majority is an emergent
  preference, not defiance. The headline uses the governing party for this
  reason; opposition numbers in `summary.csv` are descriptive only.
- **"Free" means free for backbenchers** — cabinet typically remained
  whipped on designated free votes, so residual conformity on those
  divisions is still partly whip-driven.
- Dissent frequency treats 1 rebel and 30 rebels identically; magnitude
  analyses (rebel counts, loyalty scores) are E4's task.

## Reproduction

```
python3 can_scrape.py && python3 check_data.py   # corpus must pass
python3 experiments/experiment_e1.py             # writes results_e1/
```

Outputs referenced here: `results_e1/summary.csv`,
`results_e1/whip_test_by_session.png`,
`results_e1/dissent_by_category_pooled.png`.
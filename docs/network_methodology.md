# MP voting networks: analysis and reproduction

This optional analysis extends `Party-Partisanship` without altering its underlying votes or existing outputs.

## Reproduce

With Python 3.12 and project dependencies installed, additionally run `pip install 'networkx>=3.2,<4'`.

```bash
python network_partisanship.py --sessions 38-1 42-1 44-1 --output outputs/networks-pilot
python network_partisanship.py --all --output outputs/networks-all
python network_partisanship.py --all --category government_bill --output outputs/government-network
```

Every output folder must be new (overwrite protection). First command produces the three pilot panels. Second includes every saved session. Third isolates a vote category. The script validates the saved corpus before proceeding.

The output includes `voting_networks.png`, `agreement_trends.png`, `party_agreement_heatmaps.png` (pilot sessions), `session_metrics.csv`, `party_pair_agreement.csv`, `threshold_sensitivity.csv`, and `manifest.json`.

## What is measured

For each session, construct a matrix with one row per `Person ID`, one column per recorded division, and values +1 (Yea), -1 (Nay) and 0 (no valid, single-sided vote). An MP's affiliation for the panel is their modal observed party in that session; switchers are counted. An Independent is drawn but excluded from the same-/cross-caucus pair summary because Independents do not form one caucus. All pairs must share at least 20 valid votes, and an MP must cast at least 20 valid votes to be included. `min-common` is configurable.

For MPs i,j, pairwise voting agreement is the fraction of their **jointly observed** valid votes where they made the same choice. All category filters apply before this calculation. The pairwise rate is not an ideological position and not evidence that one MP cooperated personally with another. Binary treatment excludes paired and dual-coded records, consistent with the source project's audit policy.

For every valid MP pair, the analysis calculates agreement and classifies whether both MPs are of the same party. `session_metrics.csv` records unweighted means of pair-agreement rates, their difference (`gap`), median values and the fraction of cross-party pairs with rate >= the specified threshold. `party_pair_agreement.csv` retains per-pair-of-parties averages; `threshold_sensitivity.csv` repeats cross-party edge fractions at 0.75, 0.80, 0.85 and 0.90.

Graphs use a fixed 80% agreement threshold by default (change with `--threshold`). Each MP is a node, and an edge is present when that pair exceeds the threshold with enough joint votes. The exported statistics use **every** eligible pair. For legible visualization, the drawn graph uses the strongest eight edges per node, plus up to three cross-party edges; a seeded NetworkX force layout places nodes. Thus visible edge count is deliberately less than the measured network edge count. Node positions are only qualitative; network edge fractions and pairwise agreement are the comparable quantitative evidence.

## Differences from the cited U.S. study

Andris et al. (2015), *The Rise of Partisanship and Super-Cooperators in the U.S. House of Representatives*, https://doi.org/10.1371/journal.pone.0123507, count **raw agreement votes**, and use an individually derived intersection threshold of raw-count frequency distributions in each Congress. They use a Barnes–Hut linear-attraction/linear-repulsion layout. This implementation uses normalized agreement rates, a fixed documented threshold, and NetworkX's force layout. It is an **analogue, not an exact methodological replication**; the chosen rate denominator avoids confounding comparison of different-length parliamentary sessions. The paper's label *cooperator* should not be imported as a literal interpretation of same-vote events.

## Interpretation and limitations

- Short sessions (notably 40-1, just one division) cannot support 20-common-vote pair networks, and will be marked insufficient instead of plotted as evidence of separation.
- The saved 45-1 session is an **incomplete snapshot** and must not be interpreted as a complete Parliament.
- Session coverage, party composition, confidence/procedural votes, free-vote opportunities, attendance and legislative agenda differ. These descriptive patterns do not establish causes or whipping orders.
- The affiliation used for display is modal *per period*; `party_switchers` flags known party changes. More detailed switching analyses should analyze affiliations at each division.
- Small parties may have very few MPs, affecting means and diagrams. Track pair counts (`party_pair_agreement.csv`) in interpretation.
- Some periods yield exact or near-complete clusters. An aesthetic visual split is not proof of a statistically significant partisan trend.
- For publication, preregister thresholds/windows, inspect sensitivity plots, consider bootstrap uncertainty intervals, category-weighted estimates and longitudinal comparisons of whole parliaments.

Source commit should be recorded with published charts. Source data: Canadian House of Commons' vote records, with corrections documented in this repository's `data/corrections/` and `DATA.md`.
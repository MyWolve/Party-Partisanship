"""E1: descriptive dissent by parliamentary business, with scope sensitivity.

A division counts once when at least one binary voter opposes their caucus
majority. This is not an estimate of the causal effect of a whip instruction.
"""
import argparse
import csv
from collections import defaultdict
from pathlib import Path
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
import bill_info
from check_data import require_valid_corpus, SESSIONS
from experiment_io import write_csv, write_json, plot_style
from experiments.design_checks import summarize
from visualize_parliament import WHIPPED_PARTIES, PARTY_COLORS, load_parliament, find_rebels, vote_number, count_yea_nay

RESULTS_DIR = PROJECT_ROOT / 'experiments/results_e1'
SESSION_GOVERNMENT = {s: 'Conservative' if s.split('-')[0] in ('39', '40', '41') else 'Liberal' for s in SESSIONS}
EXCLUDED_SESSIONS = {'40-1'}
UNANIMITY_THRESHOLD = .95
SCOPES = ('category_only', 'documented_free_excluded', 'uncertain_excluded', 'unknown_bill_as_government')
MAIN_SCOPE = 'documented_free_excluded'


def eligible_category(meta, status, scope):
    category = meta['category']
    if scope != 'category_only' and status == 'documented_free':
        return None
    if scope == 'uncertain_excluded' and status == 'unresolved':
        return None
    if scope == 'unknown_bill_as_government' and category == 'unknown_bill':
        return 'government_bill'
    return category


def gather_session(directory):
    metadata = bill_info.load_vote_metadata(directory)
    session = Path(directory).name.replace('Parliament_', '')
    counts = defaultdict(lambda: [0, 0])
    classifications, outliers = [], []
    for filename, votes in load_parliament(directory):
        number = vote_number(filename)
        meta = metadata[number]  # missing joins are errors, not silent omissions
        binary = [count_yea_nay(v) for v in votes.values()]
        yeas, nays = sum(v[0] for v in binary), sum(v[1] for v in binary)
        contested = bool(yeas + nays) and max(yeas, nays) / (yeas + nays) <= UNANIMITY_THRESHOLD
        rebels = find_rebels(votes, WHIPPED_PARTIES)
        for party in WHIPPED_PARTIES:
            status = bill_info.whip_status(meta, party)
            r = rebels[party]
            classifications.append(dict(session=session, division=number, party=party,
                governing=party == SESSION_GOVERNMENT[session], category=meta['category'],
                stage=meta['stage'] or '', bill=meta['bill_number'], bill_type_source=meta['bill_type_source'],
                whip_status=status['status'], member_scope=status['scope'], source_id=status['source_id'],
                majority_defined=r is not None, dissenters=len(r) if r is not None else '',
                binary_members=sum(count_yea_nay(votes[party])),
                contested=contested, subject=meta['subject']))
            if r is None:
                continue
            for scope in SCOPES:
                category = eligible_category(meta, status['status'], scope)
                if category is None:
                    continue
                for variant in ('all', 'contested') if contested else ('all',):
                    cell = counts[party, category, scope, variant]
                    cell[0] += 1
                    cell[1] += bool(r)
            if r and party == SESSION_GOVERNMENT[session] and meta['category'] == 'government_bill':
                outliers.append(dict(session=session, division=number, party=party,
                    dissenters=len(r), names='; '.join(r), whip_status=status['status'], subject=meta['subject']))
    return counts, classifications, outliers


def rate(numerator, denominator):
    return round(100 * numerator / denominator, 6) if denominator else None


def main(output_dir=None):
    require_valid_corpus()  # fail before creating/replacing any experiment output
    rows, classifications, outliers = [], [], []
    for session in SESSIONS:
        if session in EXCLUDED_SESSIONS:
            continue
        counts, audit, extremes = gather_session(PROJECT_ROOT / f'Parliament_{session}')
        classifications.extend(audit)
        outliers.extend(extremes)
        for (party, category, scope, variant), (divisions, dissent) in sorted(counts.items()):
            rows.append(dict(session=session, party=party, category=category, scope=scope,
                variant=variant, divisions=divisions, with_dissent=dissent, dissent_rate=rate(dissent, divisions)))
    gov = [r for r in rows if r['party'] == SESSION_GOVERNMENT[r['session']]]
    pooled = defaultdict(lambda: [0, 0])
    for r in gov:
        cell = pooled[r['category'], r['scope'], r['variant']]
        cell[0] += r['divisions']
        cell[1] += r['with_dissent']
    sensitivity = []
    for scope in SCOPES:
        for variant in ('all', 'contested'):
            g, p = pooled['government_bill', scope, variant], pooled['private_members_business', scope, variant]
            gr, pr = rate(g[1], g[0]), rate(p[1], p[0])
            sensitivity.append(dict(scope=scope, variant=variant, government_divisions=g[0],
                government_with_dissent=g[1], government_rate=gr, private_divisions=p[0],
                private_with_dissent=p[1], private_rate=pr,
                ratio=(round((p[1]/p[0])/(g[1]/g[0]), 6) if g[1] and p[0] else None)))
    destination = Path(output_dir or RESULTS_DIR)
    destination.mkdir(parents=True, exist_ok=True)
    write_csv(destination / 'summary.csv', rows)
    write_csv(destination / 'classification_audit.csv', classifications)
    write_csv(destination / 'sensitivity.csv', sensitivity)
    write_csv(destination / 'outliers.csv', sorted(outliers, key=lambda r: (-r['dissenters'], r['session'], r['division'])))
    bill_units, weighting, participation = summarize(classifications)
    write_csv(destination / 'bill_units.csv', bill_units)
    write_csv(destination / 'design_checks.csv', weighting)
    write_csv(destination / 'participation_checks.csv', participation)
    main_result = next(r for r in sensitivity if r['scope'] == MAIN_SCOPE and r['variant'] == 'all')
    supply = pooled['supply', MAIN_SCOPE, 'all']
    headline = dict(main_result, supply_divisions=supply[0], supply_with_dissent=supply[1],
        unresolved_governing_divisions=sum(r['governing'] and r['whip_status'] == 'unresolved' for r in classifications),
        documented_free_governing_divisions=sum(r['governing'] and r['whip_status'] == 'documented_free' for r in classifications))
    write_json(destination / 'headline.json', headline)
    plot_style()
    sessions = [s for s in SESSIONS if s not in EXCLUDED_SESSIONS]
    fig, ax = plt.subplots(figsize=(11.5, 5.8))
    for offset, category, label, color in [(-.19, 'government_bill', 'Government bills', '#254B69'),
                                          (.19, 'private_members_business', "Private members’ business", '#D49A32')]:
        selected = {r['session']: r for r in gov if r['category'] == category and r['scope'] == MAIN_SCOPE and r['variant'] == 'all'}
        for i, session in enumerate(sessions):
            r = selected.get(session)
            if r:
                ax.bar(i+offset, r['dissent_rate'], width=.36, color=color, label=label if i==0 else None)
                ax.text(i+offset, r['dissent_rate']+1, f"{r['with_dissent']}/{r['divisions']}", rotation=90, ha='center', va='bottom', fontsize=8)
            else:
                ax.text(i+offset, 1, 'N/A', ha='center', fontsize=8)
    ax.set(xticks=range(len(sessions)), xticklabels=sessions, ylim=(0, 95),
           ylabel='Divisions with governing-party dissent (%)', xlabel='Parliamentary session',
           title='Dissent is more frequent on private members’ business')
    ax.legend(loc='upper right', frameon=False)
    fig.text(.08,.015,'Labels: dissenting divisions / eligible divisions. Documented free stages excluded. P45–1 is incomplete. Category is a proxy.',fontsize=9)
    fig.tight_layout(rect=(0,.05,1,1))
    fig.savefig(destination / 'whip_test_by_session.png', dpi=180)
    plt.close(fig)
    categories = sorted({r['category'] for r in gov if r['scope'] == MAIN_SCOPE and r['variant'] == 'all'})
    fig, ax = plt.subplots(figsize=(10.5, 5.8))
    values = [pooled[c, MAIN_SCOPE, 'all'] for c in categories]
    ax.barh([c.replace('_',' ') for c in categories], [rate(d,n) for n,d in values], color='#254B69')
    for i,(n,d) in enumerate(values):
        ax.text(rate(d,n)+.4,i,f'{d}/{n}',va='center',fontsize=9)
    ax.set(xlabel='Divisions with governing-party dissent (%)', xlim=(0, max(rate(d,n) for n,d in values)+8),
           title='Governing-party dissent by business category')
    fig.text(.08,.015,'Pooled across sessions 38–1 to 45–1, excluding 40–1. Counts are divisions, not independent bills.',fontsize=9)
    fig.tight_layout(rect=(0,.05,1,1))
    fig.savefig(destination / 'dissent_by_category_pooled.png', dpi=180)
    plt.close(fig)
    h = headline
    lines = ['# E1 Dissent by parliamentary business', '',
        f"Government bills: **{h['government_with_dissent']}/{h['government_divisions']}** divisions with governing-party dissent "
        f"({h['government_rate']:.2f}%). Private members’ business: **{h['private_with_dissent']}/{h['private_divisions']}** "
        f"({h['private_rate']:.2f}%). The descriptive ratio is **{h['ratio']:.2f}**.", '',
        f"Supply: **{supply[1]}/{supply[0]}**. The main comparison excludes {h['documented_free_governing_divisions']} "
        f"documented free stages for the governing party. There are {h['unresolved_governing_divisions']} "
        'governing-party divisions with explicitly unresolved status; see sensitivity below.', '',
        '## Sensitivity', '',
        '| Scope | Government dissent | Private business dissent | Ratio |', '| --- | --- | --- | --- |']
    for r in sensitivity:
        if r['variant']=='all':
            lines.append(f"| {r['scope'].replace('_',' ')} | {r['government_with_dissent']}/{r['government_divisions']} | "
                         f"{r['private_with_dissent']}/{r['private_divisions']} | {r['ratio']:.2f} |")
    lines += ['', 'Category only retains documented free stages. The main comparison removes them. '
        'Uncertain excluded additionally removes audited unresolved cases; it does not imply that the remainder has verified whip instructions. '
        'Unknown bill as government tests the malformed bill subject separately. The CSV also contains contested-only versions '
        '(no more than 95% of observed binary House votes on either side).', '',
        '## Repeated bills and participating caucus size', '',
        '| Category | All divisions | Numbered-bill divisions | Equal bill mean | Session–bill units | Unnumbered divisions omitted from bill check |',
        '| --- | --- | --- | --- | --- | --- |']
    for r in weighting:
        lines.append(f"| {r['category']} | {r['all_division_rate']:.2f}% | {r['numbered_division_rate']:.2f}% | "
                     f"{r['equal_bill_mean_rate']:.2f}% | {r['session_bill_units']} | {r['unnumbered_divisions']} |")
    lines += ['', 'The equal-bill mean first computes each session–bill’s fraction of eligible divisions containing dissent, '
        'then weights those bills equally. It is not the fraction of bills with any dissent. Bill numbers restart across sessions; '
        'the key includes session. The numbered-only division rate separates selection changes from weighting changes. '
        'Private members’ motions without a bill number remain in the headline but cannot enter this bill-level comparison. '
        'Reintroduced bills can still be related across sessions; no independence or causal claim follows.', '',
        '| Category | Observed party voters | Divisions | Divisions with dissent | Minority member-votes |',
        '| --- | --- | --- | --- | --- |']
    for r in participation:
        dr = f"{r['division_dissent_rate']:.2f}%" if r['divisions'] else 'undefined'
        mr = f"{r['minority_member_vote_rate']:.2f}%" if r['binary_member_votes'] else 'undefined'
        lines.append(f"| {r['category']} | {r['observed_party_voters']} | {r['divisions']} | {dr} | {mr} |")
    lines += ['', 'Size bands count observed unpaired binary voters in the governing party, not seats or the full caucus roster. '
        'Bands (1–100, 101–150, 151+) are descriptive; they do not adjust for session, issue, attendance or bill composition. '
        'The minority member-vote rate divides minority votes by all eligible binary member-votes, so it measures intensity '
        'and weights larger participating groups more heavily. Tied majorities and documented free stages are excluded throughout. '
        'These are diagnostics of denominator choices, not an estimated effect of caucus size. '
        'Inspect [bill units](bill_units.csv), [weighting](design_checks.csv), and [participation](participation_checks.csv).', '',
        '## Interpretation and limits', '',
        'These are descriptive associations between business types and caucus voting patterns. They do not isolate the effect of whip enforcement. '
        'Issues, participating MPs, caucus size, repeated divisions on the same bill, and party policy can all differ across categories. '
        'One dissenter and many dissenters count equally. Tied caucus divisions have no majority and are excluded from this outcome. '
        'Paired and dual-coded member-votes are omitted from binary analysis. No uncertainty interval assuming independent divisions is asserted.', '',
        'C-38 and C-14 designations are party- and stage-specific. Liberal designations cover backbenchers, not cabinet; '
        'the exclusion applies at the caucus-division level and is not an MP-level freedom label. C-30, C-17, recommittal, '
        'and C-14 Senate-amendment coverage remain unresolved where listed. Business category and confidence keywords are proxies. '
        'The observed government-bill rate is not asserted to be an upper bound on true whipped dissent.', '',
        'See [classification audit](classification_audit.csv), [outliers and names](outliers.csv), '
        '[all counts](summary.csv), [sensitivity](sensitivity.csv), [source decisions](../../audit/whip_designations.json), '
        'and [reproduction instructions](../../REPRODUCING.md).']
    (destination / 'FINDINGS_E1.md').write_text('\n'.join(lines)+'\n',encoding='utf-8',newline='\n')
    print('E1:', headline)
    return headline


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir',type=Path)
    main(parser.parse_args().output_dir)

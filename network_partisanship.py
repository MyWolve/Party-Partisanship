"""Voting-agreement networks for the Canadian House of Commons.

Runs against the frozen Party-Partisanship corpus without changing its inputs.
The primary metric is MP-pair agreement conditional on BOTH MPs casting a
single-sided Yea/Nay vote. This is a participation-adjusted extension of
Andris et al. (2015), whose original threshold used RAW agreement counts.

Usage:
  python network_partisanship.py --sessions 38-1 42-1 44-1 --output outputs/networks-pilot
  python network_partisanship.py --all --output outputs/networks-all
  python network_partisanship.py --all --category government_bill --output outputs/government-networks

Additional dependency: networkx>=3.2. The repo's original requirements
already include NumPy and Matplotlib.
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
import networkx as nx
import numpy as np

from bill_info import load_vote_metadata
from check_data import SESSIONS, require_valid_corpus
from vote_data import ROOT, binary_vote, read_vote_rows
from visualize_parliament import AFFILIATION_ALIASES, PARTIES, PARTY_COLORS

PILOT = ('38-1', '42-1', '44-1')
SENSITIVITY = (0.75, 0.80, 0.85, 0.90)
PARTY_ORDER = ('Liberal', 'Conservative', 'NDP', 'Bloc Québécois', 'Green Party', 'Independent')


@dataclass
class Period:
    session: str
    divisions: int
    eligible_members: int
    member_observations: int
    party_switchers: int
    eligible_pairs: int
    same_party_pairs: int
    cross_party_pairs: int
    mean_same: float | None
    mean_cross: float | None
    gap: float | None
    median_same: float | None
    median_cross: float | None
    threshold: float
    graph_edges: int
    graph_cross_edges: int
    cross_edge_share: float | None
    assortativity: float | None
    status: str


def read_session(session: str, category: str | None = None) -> tuple[list[str], list[str], np.ndarray, int]:
    """Make an MP x division array: +1 Yea; -1 Nay; 0 no valid vote.

    Members are keyed by stable person ID, with each period's party determined
    by their most frequently observed affiliation (not by name). Independents
    remain separately classified; affiliation changes are counted and flagged.
    """
    directory = ROOT / f'Parliament_{session}'
    metadata = load_vote_metadata(directory)
    divisions = [(number, record) for number, record in sorted(metadata.items())
                 if category is None or record['category'] == category]
    observed: dict[str, dict[int, int]] = defaultdict(dict)
    affiliations: dict[str, Counter] = defaultdict(Counter)
    labels: dict[str, str] = {}
    for d_index, (number, _) in enumerate(divisions):
        for row in read_vote_rows(directory / f'file_{number}.csv'):
            person_id = row['member_id']
            if not person_id:
                raise ValueError(f'{session}/{number}: missing stable person ID')
            party = AFFILIATION_ALIASES.get(row['party'], row['party'])
            if party not in PARTIES:
                party = 'Independent'
            vote = binary_vote(row)
            if vote not in ('Yea', 'Nay'):
                continue
            observed[person_id][d_index] = 1 if vote == 'Yea' else -1
            affiliations[person_id][party] += 1
            labels[person_id] = row['member']
    ids = sorted(observed)
    party = [sorted(affiliations[i].items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
             for i in ids]
    X = np.zeros((len(ids), len(divisions)), dtype=np.float32)
    for idx, key in enumerate(ids):
        for d, vote in observed[key].items():
            X[idx, d] = vote
    switchers = sum(len([p for p, n in affiliations[i].items() if n]) > 1 for i in ids)
    return ids, party, X, switchers


def similarity(X: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return rate, raw equal-vote counts, and joint observed counts (NxN)."""
    if X.ndim != 2:
        raise ValueError('Expected an MP x division matrix')
    valid = (X != 0).astype(np.float32)
    coobs = valid @ valid.T
    # identity +1 for identical votes and -1 for opposite, so (N+dot)/2
    counts = np.rint((coobs + X @ X.T) / 2).astype(np.int32)
    rates = np.divide(counts, coobs, out=np.full_like(coobs, np.nan), where=coobs > 0)
    np.fill_diagonal(rates, np.nan)
    return rates, counts, coobs


def pair_mask(party: list[str], coobs: np.ndarray, min_common: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    n = len(party)
    if n == 0:
        return (np.zeros((0, 0), bool),) * 3
    labels = np.asarray(party, dtype=str)
    active = labels != 'Independent'
    mask = np.triu(coobs >= min_common, 1) & active[:, None] & active[None, :]
    same = mask & (labels[:, None] == labels[None, :])
    cross = mask & (labels[:, None] != labels[None, :])
    return mask, same, cross


def cell_metrics(session: str, X: np.ndarray, party: list[str], min_common: int,
                 threshold: float, switchers: int) -> tuple[Period, dict, np.ndarray, np.ndarray, np.ndarray]:
    # A minimum of min_common cast votes avoids making a plot out of one or two divisions.
    participation = (X != 0).sum(axis=1)
    keep = participation >= min_common
    X = X[keep]
    party = [p for p, yes in zip(party, keep) if yes]
    if len(party) < 2:
        period = Period(session, X.shape[1], len(party), int(participation.sum()), switchers,
                        0, 0, 0, None, None, None, None, None, threshold, 0, 0,
                        None, None, 'insufficient_data')
        return period, {}, X, np.zeros((len(party), len(party)), dtype=float), np.zeros((len(party), len(party)), dtype=bool)
    agreement, _, coobs = similarity(X)
    valid_pairs, sp, cp = pair_mask(party, coobs, min_common)
    sp_values, cp_values = agreement[sp], agreement[cp]
    edges = valid_pairs & (agreement >= threshold)
    e = int(edges.sum())
    c = int((edges & cp).sum())
    metrics = Period(
        session=session, divisions=X.shape[1], eligible_members=len(party),
        member_observations=int((X != 0).sum()), party_switchers=switchers,
        eligible_pairs=int(valid_pairs.sum()), same_party_pairs=len(sp_values),
        cross_party_pairs=len(cp_values),
        mean_same=float(sp_values.mean()) if len(sp_values) else None,
        mean_cross=float(cp_values.mean()) if len(cp_values) else None,
        gap=float(sp_values.mean()-cp_values.mean()) if len(sp_values) and len(cp_values) else None,
        median_same=float(np.median(sp_values)) if len(sp_values) else None,
        median_cross=float(np.median(cp_values)) if len(cp_values) else None,
        threshold=threshold, graph_edges=e, graph_cross_edges=c,
        cross_edge_share=c/len(cp_values) if len(cp_values) else None,
        assortativity=None, status='ok' if len(sp_values) and len(cp_values) else 'insufficient_pairs'
    )
    party_pairs: dict[tuple[str, str], list[float]] = defaultdict(list)
    for i, j in zip(*np.where(valid_pairs)):
        a, b = sorted((party[i], party[j]))
        party_pairs[(a, b)].append(float(agreement[i, j]))
    summary = {(a, b): (len(v), float(np.mean(v)), float(np.median(v)))
               for (a, b), v in party_pairs.items()}
    if e:
        G = nx.Graph()
        G.add_nodes_from((i, {'party': p}) for i, p in enumerate(party) if p != 'Independent')
        G.add_edges_from((int(i), int(j)) for i, j in zip(*np.where(edges)))
        if G.number_of_edges():
            assortativity = nx.attribute_assortativity_coefficient(G, 'party')
            metrics.assortativity = float(assortativity) if np.isfinite(assortativity) else None
    return metrics, summary, X, agreement, edges


def layout_graph(agreement: np.ndarray, edges: np.ndarray, party: list[str], seed: int = 7,
                 neighbors: int = 8) -> tuple[np.ndarray, np.ndarray]:
    """Sparse force layout derived from thresholded network; full edges are kept for statistics.

    Visual clutter is limited by retaining up to 'neighbors' strongest eligible
    connections per node (incl. up to three out-of-party connections).
    """
    n = len(party)
    if not n:
        return np.zeros((0, 2)), np.zeros((0, 2), dtype=int)
    G = nx.Graph()
    G.add_nodes_from(range(n))
    keep_edges = set()
    for i in range(n):
        js = np.where(edges[i] | edges[:, i])[0]
        if not len(js):
            continue
        order = sorted(js, key=lambda j: (-float(agreement[i, j]), int(j)))
        selected = order[:neighbors]
        cross = [j for j in order if party[j] != party[i]][:3]
        for j in selected + cross:
            u, v = sorted((i, int(j)))
            if u != v:
                keep_edges.add((u, v))
    for i, j in sorted(keep_edges):
        G.add_edge(i, j, weight=float(0.05 + agreement[i, j]))
    pos = nx.spring_layout(G, seed=seed, iterations=85, weight='weight', scale=1.0)
    xy = np.asarray([pos[i] for i in range(n)], dtype=float)
    # Keep Liberal on left and Conservative on right for comparisons where both exist.
    lp = xy[[i for i, p in enumerate(party) if p == 'Liberal']]
    cp = xy[[i for i, p in enumerate(party) if p == 'Conservative']]
    if len(lp) and len(cp):
        vector = cp.mean(axis=0)-lp.mean(axis=0)
        angle = -np.arctan2(vector[1], vector[0])
        rot = np.array([[np.cos(angle), -np.sin(angle)],
                        [np.sin(angle), np.cos(angle)]])
        xy = xy @ rot.T
    return xy, np.asarray(sorted(keep_edges), dtype=int).reshape(-1, 2)


def render_network(ax, metric: Period, xy: np.ndarray, shown_edges: np.ndarray,
                   party: list[str], party_colours: dict) -> None:
    ax.set_title(metric.session, fontsize=11, fontweight='bold')
    if metric.status != 'ok':
        ax.text(.5, .5, f'Insufficient data\n({metric.divisions} recorded divisions)',
                transform=ax.transAxes, ha='center', va='center', fontsize=10)
        ax.axis('off')
        return
    if len(shown_edges):
        lc = LineCollection(xy[shown_edges], colors='#7e8997', alpha=.15, linewidths=.32, zorder=1)
        ax.add_collection(lc)
    party_array = np.asarray(party)
    for label in PARTY_ORDER:
        loc = party_array == label
        if loc.any():
            ax.scatter(xy[loc, 0], xy[loc, 1], s=7.0, alpha=.80, linewidths=0,
                       color=party_colours[label], label=label, rasterized=True, zorder=2)
    ax.set_xlim(xy[:, 0].min()-.13, xy[:, 0].max()+.13)
    ax.set_ylim(xy[:, 1].min()-.13, xy[:, 1].max()+.13)
    ax.set_aspect('equal', adjustable='box')
    ax.axis('off')
    ax.text(.5, -.035, f'{metric.divisions:,} votes · {metric.eligible_members} MPs · '
            f'gap {100*metric.gap:.1f} pp', transform=ax.transAxes,
            ha='center', va='top', fontsize=7.1, color='#454b54')


def save_panel_grid(rows: list[tuple[Period, np.ndarray, np.ndarray, list[str]]],
                    destination: Path, title: str) -> None:
    count = len(rows)
    ncols = 3 if count <= 3 else 4
    nrows = (count + ncols-1)//ncols
    fig, axs = plt.subplots(nrows, ncols, figsize=(ncols*4.1, nrows*3.2), squeeze=False)
    for ax in axs.flat:
        ax.axis('off')
    for ax, (metric, xy, edges, party) in zip(axs.flat, rows):
        render_network(ax, metric, xy, edges, party, PARTY_COLORS)
    present = {p for _, _, _, parties in rows for p in parties}
    markers = [plt.Line2D([0], [0], marker='o', linestyle='', color=PARTY_COLORS[p],
                          label=p, markersize=6) for p in PARTY_ORDER if p in present]
    fig.suptitle(title, fontsize=15, y=.985)
    fig.legend(handles=markers, loc='lower center', ncol=max(1, min(6, len(markers))), frameon=False,
               fontsize=8, bbox_to_anchor=(.5, .085))
    fig.text(.5, .042, 'Drawn edges are sparsified for legibility; all eligible pairs enter the statistics. '
             'Paired, dual-coded and absent votes are excluded.',
             ha='center', fontsize=8)
    fig.tight_layout(rect=(0, .16, 1, .945), w_pad=.8, h_pad=2.0)
    fig.savefig(destination, dpi=190, bbox_inches='tight')
    plt.close(fig)


def save_trends(metrics: list[Period], destination: Path) -> None:
    fig, (ax, bx) = plt.subplots(2, 1, figsize=(12, 7), sharex=True)
    x = np.arange(len(metrics))
    valid = [i for i, m in enumerate(metrics) if m.status == 'ok']
    for values, label, col in [([m.mean_same for m in metrics], 'Same-party', '#1f69a6'),
                               ([m.mean_cross for m in metrics], 'Cross-party', '#d05757')]:
        ax.plot(valid, [100*values[i] for i in valid], '-o', label=label, color=col, lw=2, ms=5)
    ax.set_ylabel('Mean MP-pair agreement (%)')
    ax.legend(frameon=False)
    ax.grid(alpha=.2)
    bx.bar(valid, [100*metrics[i].gap for i in valid], color='#5c7188')
    bx.set_ylabel('Agreement gap (percentage points)')
    bx.grid(axis='y', alpha=.2)
    bx.set_xticks(x, [m.session for m in metrics], rotation=45)
    ax.set_title('Canadian MP voting agreement by parliamentary session')
    fig.text(.5, .01, 'Based on available recorded divisions; sessions vary in duration and vote composition. '
             'Missing/short sessions are not interpolated.', ha='center', fontsize=8)
    fig.tight_layout(rect=(0, .05, 1, 1))
    fig.savefig(destination, dpi=180)
    plt.close(fig)


def save_party_pair_trends(pair_rows: list[dict], sessions: list[str], destination: Path) -> None:
    """Plot selected cross-party relationships rather than collapsing every party pair."""
    relations = [('Liberal', 'Conservative'), ('Liberal', 'NDP'),
                 ('Conservative', 'NDP'), ('Bloc Québécois', 'Liberal')]
    indexed = {(r['session'], r['party_a'], r['party_b']): r['mean_agreement']
               for r in pair_rows}
    x = np.arange(len(sessions))
    fig, ax = plt.subplots(figsize=(12, 5.5))
    for party_a, party_b in relations:
        a, b = sorted((party_a, party_b))
        values = [indexed.get((session, a, b), float('nan')) for session in sessions]
        ax.plot(x, np.array(values) * 100, '-o', linewidth=2, markersize=4.5,
                label=f'{party_a}–{party_b}')
    ax.set_xticks(x, sessions, rotation=45)
    ax.set_ylim(0, 100)
    ax.set_ylabel('Mean pair agreement across jointly observed votes (%)')
    ax.set_title('Canadian cross-party voting relationships by parliamentary session')
    ax.grid(alpha=.2)
    ax.legend(loc='upper center', ncol=2, frameon=False)
    fig.text(.5, .015, 'All eligible MP pairs; absent and paired votes excluded. '
             'The 45-1 session is an incomplete snapshot.', ha='center', fontsize=8)
    fig.tight_layout(rect=(0, .05, 1, 1))
    fig.savefig(destination, dpi=180)
    plt.close(fig)


def save_heatmaps(period_pair_rows: list[dict], sessions: list[str], destination: Path) -> None:
    sessions = [s for s in sessions if any(p['session'] == s for p in period_pair_rows)]
    if not sessions:
        return
    party_names = [p for p in PARTY_ORDER if p != 'Independent']
    fig, axs = plt.subplots(1, len(sessions), figsize=(4.4*len(sessions), 5), squeeze=False)
    for ax, session in zip(axs.flat, sessions):
        relevant = {(r['party_a'], r['party_b']): r['mean_agreement']
                    for r in period_pair_rows if r['session'] == session}
        z = np.full((len(party_names), len(party_names)), np.nan)
        for i, a in enumerate(party_names):
            for j, b in enumerate(party_names):
                z[i, j] = relevant.get(tuple(sorted((a, b))), np.nan)
        cmap = plt.get_cmap('viridis').copy()
        cmap.set_bad('#edf0f4')
        im = ax.imshow(z, cmap=cmap, vmin=0.3, vmax=1)
        for i in range(len(party_names)):
            for j in range(len(party_names)):
                if np.isfinite(z[i, j]):
                    ax.text(j, i, f'{100*z[i,j]:.0f}', ha='center', va='center',
                            fontsize=8, color='white' if z[i,j]<.64 else 'black')
        ax.set_xticks(range(len(party_names)), party_names, rotation=50, ha='right')
        ax.set_yticks(range(len(party_names)), party_names)
        ax.set_title(session)
    fig.colorbar(im, ax=axs.ravel().tolist(), shrink=.7, label='Mean pair agreement')
    fig.suptitle('Voting agreement between and within parties (%)', fontsize=14)
    fig.subplots_adjust(left=.11, right=.91, bottom=.21, top=.84, wspace=.7)
    fig.savefig(destination, dpi=180, bbox_inches='tight')
    plt.close(fig)


def export_csv(path: Path, rows: list[dict], headers: list[str]):
    with path.open('w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=headers)
        w.writeheader()
        w.writerows(rows)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    selector = parser.add_mutually_exclusive_group()
    selector.add_argument('--sessions', nargs='+', choices=SESSIONS, default=list(PILOT))
    selector.add_argument('--all', action='store_true', help='All saved sessions (including short/incomplete ones)')
    parser.add_argument('--category', help='Classified vote category, e.g. government_bill')
    parser.add_argument('--parties', nargs='+', choices=PARTY_ORDER,
                        help='Limit plotted/analyzed MPs to specified parties, e.g. Liberal Conservative')
    parser.add_argument('--threshold', type=float, default=.80,
                        help='Minimum fraction of jointly cast votes for network links (default 0.80)')
    parser.add_argument('--min-common', type=int, default=20,
                        help='Minimum number of jointly observed divisions for each pair and each MP')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--seed', type=int, default=7)
    parser.add_argument('--skip-validation', action='store_true', help='Development only; skip corpus audit')
    args = parser.parse_args(argv)
    if not 0 <= args.threshold <= 1 or args.min_common < 2:
        parser.error('threshold must be in [0,1] and min-common at least 2')
    sessions = list(SESSIONS) if args.all else args.sessions
    if not args.skip_validation:
        require_valid_corpus(sessions=sessions)
    args.output.mkdir(parents=True, exist_ok=False)
    metrics, pair_rows, sensitivity, panels = [], [], [], []
    for session in sessions:
        ids, party_all, X0, switchers = read_session(session, args.category)
        if args.parties:
            selected = np.asarray([p in args.parties for p in party_all], dtype=bool)
            X0 = X0[selected]
            party_all = [p for p, yes in zip(party_all, selected) if yes]
        m, party_summary, X, agreement, edges = cell_metrics(session, X0, party_all,
                                                               args.min_common, args.threshold, switchers)
        keep = (X0 != 0).sum(axis=1) >= args.min_common
        party = [p for p, yes in zip(party_all, keep) if yes]
        metrics.append(m)
        for (a, b), (n, avg, median) in sorted(party_summary.items()):
            pair_rows.append(dict(session=session, party_a=a, party_b=b,
                                  pairs=n, mean_agreement=avg, median_agreement=median))
        if m.status == 'ok':
            mask, _, cp = pair_mask(party, (X != 0).astype(np.float32) @ (X != 0).astype(np.float32).T,
                                    args.min_common)
            for t in SENSITIVITY:
                sensitivity.append(dict(session=session, threshold=t,
                                        eligible_cross_pairs=int(cp.sum()),
                                        cross_pairs_above=int((cp & (agreement >= t)).sum()),
                                        cross_pair_fraction=float((cp & (agreement >= t)).sum()/cp.sum())))
            xy, shown = layout_graph(agreement, edges, party, seed=args.seed)
            panels.append((m, xy, shown, party))
        else:
            panels.append((m, np.zeros((len(party), 2)), np.zeros((0, 2), int), party))
        print(f'{session}: {m.divisions} divisions | {m.eligible_members} MPs | '
              f'same={m.mean_same} cross={m.mean_cross} | status={m.status}', flush=True)
    export_csv(args.output/'session_metrics.csv', [asdict(m) for m in metrics], list(Period.__dataclass_fields__))
    export_csv(args.output/'party_pair_agreement.csv', pair_rows,
               ['session', 'party_a', 'party_b', 'pairs', 'mean_agreement', 'median_agreement'])
    export_csv(args.output/'threshold_sensitivity.csv', sensitivity,
               ['session', 'threshold', 'eligible_cross_pairs', 'cross_pairs_above', 'cross_pair_fraction'])
    save_panel_grid(panels, args.output/'voting_networks.png',
                    'Canadian House of Commons: networks of voting agreement')
    save_trends(metrics, args.output/'agreement_trends.png')
    save_party_pair_trends(pair_rows, sessions, args.output/'cross_party_trends.png')
    save_heatmaps(pair_rows, [s for s in PILOT if s in sessions], args.output/'party_agreement_heatmaps.png')
    (args.output/'manifest.json').write_text(json.dumps({
        'schema': 1, 'sessions': sessions, 'category': args.category,
        'threshold': args.threshold, 'min_common': args.min_common, 'parties': args.parties,
        'seed': args.seed, 'source': 'MyWolve/Party-Partisanship; original files unmodified',
        'method': 'Normalized identical Yea/Nay decisions among jointly observed divisions',
        'important': 'Not an exact replication of Andris et al. 2015 raw-count threshold; '
                     'short periods, free votes and category composition can change patterns.'
    }, indent=2)+'\n', encoding='utf-8')
    print(f'Wrote analysis to {args.output}')


if __name__ == '__main__':
    main()
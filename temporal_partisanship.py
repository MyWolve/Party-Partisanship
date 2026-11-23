"""Within-session parliamentary voting agreement: independent, cumulative and rolling windows.

This module is called by ``network_partisanship.py --temporal-mode quarterly``.
All voting observations are read from the audited, frozen source files. It makes
no changes to source records and no claims about ideology or whip instructions.
"""
from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

from bill_info import load_vote_metadata
from vote_data import ROOT, read_vote_rows, binary_vote
from visualize_parliament import AFFILIATION_ALIASES, PARTIES, PARTY_COLORS
from network_partisanship import (PARTY_ORDER, Period, cell_metrics, layout_graph,
                                   render_network, similarity, export_csv)


@dataclass(frozen=True)
class Window:
    mode: str
    label: str
    start: int  # zero-based inclusive
    end: int    # zero-based exclusive
    index: int


@dataclass
class Corpus:
    session: str
    ids: list[str]
    labels: dict[str, str]
    votes: np.ndarray         # members x ordered divisions; +1/-1/0
    affiliations: np.ndarray  # same shape, party integer (or -1 for absent)
    divisions: list[int]
    dates: list[str]
    categories: list[str]
    bills: list[str]


@dataclass
class Result:
    window: Window
    metric: Period
    ids: list[str]
    parties: list[str]
    X: np.ndarray
    agreement: np.ndarray
    edges: np.ndarray
    xy: np.ndarray
    shown: np.ndarray
    pair_summary: dict


def quarter_windows(n: int) -> list[Window]:
    """Partition n chronological division observations into 4 disjoint periods."""
    if n < 0:
        raise ValueError('Division count cannot be negative')
    borders = [n * k // 4 for k in range(5)]
    return [Window('independent', f'Q{i+1}', borders[i], borders[i+1], i+1)
            for i in range(4)]


def cumulative_windows(n: int) -> list[Window]:
    return [Window('cumulative', f'Through Q{q.index}', 0, q.end, q.index)
            for q in quarter_windows(n)]


def rolling_windows(n: int, width: int, step: int) -> list[Window]:
    if width <= 0 or step <= 0:
        raise ValueError('width and step must be positive')
    if n == 0:
        return [Window('rolling', 'R1', 0, 0, 1)]
    if n <= width:
        return [Window('rolling', 'R1', 0, n, 1)]
    starts = list(range(0, n-width+1, step))
    if starts[-1] != n-width:
        starts.append(n-width)
    return [Window('rolling', f'R{i+1}', a, a+width, i+1)
            for i, a in enumerate(starts)]


def load_corpus(session: str, category: str | None = None) -> Corpus:
    """Read votes once per session, with the recorded party on each division.

    Division numbers are the canonical chronological order: the source's date
    metadata sometimes has intraday clock inconsistencies. Dates are retained
    separately for interpretation and reporting.
    """
    directory = ROOT / f'Parliament_{session}'
    metadata = load_vote_metadata(directory)
    selected = [(n, r) for n, r in sorted(metadata.items())
                if category is None or r['category'] == category]
    by_id: dict[str, dict[int, tuple[int, int]]] = defaultdict(dict)
    labels = {}
    for k, (number, _) in enumerate(selected):
        for r in read_vote_rows(directory / f'file_{number}.csv'):
            person = r['member_id']
            if not person:
                raise ValueError(f'{session}/{number}: member lacks stable Person ID')
            party = AFFILIATION_ALIASES.get(r['party'], r['party'])
            if party not in PARTIES:
                party = 'Independent'
            vote = binary_vote(r)
            if vote not in ('Yea', 'Nay'):
                continue  # Pairing and both-sided flags are not voting decisions.
            by_id[person][k] = (1 if vote == 'Yea' else -1, PARTY_ORDER.index(party))
            labels[person] = r['member']
    ids = sorted(by_id)
    v = np.zeros((len(ids), len(selected)), dtype=np.float32)
    affiliation = np.full((len(ids), len(selected)), -1, dtype=np.int8)
    for i, person in enumerate(ids):
        for j, (vote, party_code) in by_id[person].items():
            v[i, j] = vote
            affiliation[i, j] = party_code
    return Corpus(session, ids, labels, v, affiliation,
                  [n for n, _ in selected], [r['date'] for _, r in selected],
                  [r['category'] for _, r in selected],
                  [f'{session}/{r["bill_number"]}' if r.get('bill_number') else ''
                   for _, r in selected])


def window_parties(affiliations: np.ndarray) -> tuple[list[str], int]:
    """Assign each MP's party *inside the window*, not their overall caucus."""
    parties, switchers = [], 0
    for observed in affiliations:
        counts = Counter(int(x) for x in observed if x >= 0)
        if len(counts) > 1:
            switchers += 1
        party_num = min(counts, key=lambda k: (-counts[k], k)) if counts else -1
        parties.append(PARTY_ORDER[party_num] if party_num >= 0 else 'Independent')
    return parties, switchers


def evaluate(corpus: Corpus, window: Window, *, threshold: float = .80,
             min_common: int = 20, min_window_divisions: int = 40,
             selected_parties: list[str] | None = None,
             draw: bool = False, seed: int = 7) -> Result:
    votes = corpus.votes[:, window.start:window.end]
    affiliations = corpus.affiliations[:, window.start:window.end]
    parties, switchers = window_parties(affiliations)
    active = (votes != 0).sum(axis=1) >= min_common
    if selected_parties:
        active &= np.array([p in selected_parties for p in parties], dtype=bool)
    filtered_x = votes[active]
    filtered_ids = [p for p, included in zip(corpus.ids, active) if included]
    filtered_parties = [p for p, included in zip(parties, active) if included]
    # This function's member-count and pair-count semantics match the base analysis.
    metric, summary, x, agreement, edges = cell_metrics(
        f'{corpus.session} {window.label}', filtered_x, filtered_parties,
        min_common, threshold, switchers)
    if window.end-window.start < min_window_divisions:
        metric.status = 'insufficient_window'
        summary = {}
    if draw and metric.status == 'ok':
        xy, shown = layout_graph(agreement, edges, filtered_parties, seed=seed)
    else:
        xy = np.zeros((len(filtered_ids), 2), dtype=float)
        shown = np.zeros((0, 2), dtype=int)
    return Result(window, metric, filtered_ids, filtered_parties, x,
                  agreement, edges, xy, shown, summary)


def adjacency_correspondence(a: Result, b: Result, min_common: int) -> dict:
    """Compare actual pair agreement across snapshots, not layout coordinates.

    The same unordered pairs of stable MP IDs are evaluated in both periods;
    a pair must have at least ``min_common`` jointly observed votes in each.
    """
    common = sorted(set(a.ids) & set(b.ids))
    if a.metric.status != 'ok' or b.metric.status != 'ok':
        return dict(common_mps=len(common), comparable_pairs=0,
                    agreement_correlation=None, edge_jaccard=None,
                    edges_gained=0, edges_lost=0)
    if len(common) < 2:
        return dict(common_mps=len(common), comparable_pairs=0,
                    agreement_correlation=None, edge_jaccard=None,
                    edges_gained=0, edges_lost=0)
    ia = np.array([a.ids.index(p) for p in common])
    ib = np.array([b.ids.index(p) for p in common])
    pa = a.parties
    pb = b.parties
    # Independents do not form a parliamentary caucus, but can have individual
    # edges. Here exclude them in either window to match published metric scope.
    permitted = np.array([pa[x] != 'Independent' and pb[y] != 'Independent'
                          for x, y in zip(ia, ib)])
    va, vb = a.X[ia], b.X[ib]
    na = (va != 0).astype(np.float32) @ (va != 0).astype(np.float32).T
    nb = (vb != 0).astype(np.float32) @ (vb != 0).astype(np.float32).T
    eligible = np.triu((na >= min_common) & (nb >= min_common), 1)
    eligible &= permitted[:, None] & permitted[None, :]
    ra, rb = a.agreement[np.ix_(ia, ia)], b.agreement[np.ix_(ib, ib)]
    eligible &= np.isfinite(ra) & np.isfinite(rb)
    xx, yy = ra[eligible], rb[eligible]
    if not len(xx):
        return dict(common_mps=len(common), comparable_pairs=0,
                    agreement_correlation=None, edge_jaccard=None,
                    edges_gained=0, edges_lost=0)
    corr = None
    if len(xx) > 1 and np.std(xx) > 1e-12 and np.std(yy) > 1e-12:
        corr = float(np.corrcoef(xx, yy)[0, 1])
    ea, eb = a.edges[np.ix_(ia, ia)][eligible], b.edges[np.ix_(ib, ib)][eligible]
    union = int((ea | eb).sum())
    return dict(common_mps=len(common), comparable_pairs=len(xx),
                agreement_correlation=corr,
                edge_jaccard=float((ea & eb).sum()/union) if union else None,
                edges_gained=int((~ea & eb).sum()), edges_lost=int((ea & ~eb).sum()))


def party_profiles(result: Result, min_common: int) -> list[dict]:
    """Each MP's average voting agreement with every caucus (leave-one-out)."""
    if not len(result.ids):
        return []
    valid = (result.X != 0).astype(np.float32)
    coobs = valid @ valid.T
    out = []
    for i, person in enumerate(result.ids):
        peers = (coobs[i] >= min_common) & np.isfinite(result.agreement[i])
        row = dict(member_id=person, party=result.parties[i],
                   votes_cast=int(valid[i].sum()), window=result.window.label,
                   mode=result.window.mode)
        for p in PARTY_ORDER:
            group = peers & (np.asarray(result.parties) == p)
            row[p] = float(np.mean(result.agreement[i, group])) if group.any() else None
        out.append(row)
    return out


def profile_change(a: list[dict], b: list[dict]) -> list[dict]:
    """Adjacent-quarter distances across comparable party-affinity coordinates."""
    prev = {r['member_id']: r for r in a}
    out = []
    for current in b:
        old = prev.get(current['member_id'])
        if old is None:
            continue
        valid = [(float(old[p]), float(current[p])) for p in PARTY_ORDER if p != 'Independent'
                 if old.get(p) is not None and current.get(p) is not None]
        if not valid:
            continue
        diffs = np.array([z-y for y, z in valid])
        out.append(dict(member_id=current['member_id'],
                        previous_window=old['window'], current_window=current['window'],
                        from_party=old['party'], to_party=current['party'],
                        affiliation_changed=int(old['party'] != current['party']),
                        common_party_dimensions=len(valid),
                        rms_party_affinity_change=float(np.sqrt(np.mean(diffs**2))),
                        max_abs_party_affinity_change=float(np.max(np.abs(diffs)))))
    return out


def align_common_id_positions(reference: Result, moving: Result) -> None:
    """Rotate/translate each layout to common stable-ID nodes, no reflection.

    This is a *display stabilization* only; numerical correspondence is based
    on observed votes (adjacency_correspondence), never Euclidean layout drift.
    """
    common = sorted(set(reference.ids) & set(moving.ids))
    if len(common) < 3 or not len(reference.xy) or not len(moving.xy):
        return
    ar = np.array([reference.ids.index(i) for i in common])
    am = np.array([moving.ids.index(i) for i in common])
    ref, mov = reference.xy[ar], moving.xy[am]
    refmean, movmean = ref.mean(axis=0), mov.mean(axis=0)
    refcenter, movcenter = ref-refmean, mov-movmean
    u, _, vt = np.linalg.svd(movcenter.T @ refcenter)
    rot = u @ vt
    if np.linalg.det(rot) < 0:
        u[:, -1] *= -1
        rot = u @ vt
    moving.xy = (moving.xy-movmean) @ rot + refmean


def save_atlas(all_results: dict[str, list[Result]], path: Path, title: str) -> None:
    sessions = list(all_results)
    nrows = len(sessions)
    if not nrows:
        return
    fig, axs = plt.subplots(nrows, 4, figsize=(17, 3.8*nrows), squeeze=False)
    for r, session in enumerate(sessions):
        results = all_results[session]
        good = [x for x in results if x.metric.status == 'ok']
        if good:
            anchor = good[0]
            for x in good[1:]:
                align_common_id_positions(anchor, x)
            joined = np.vstack([x.xy for x in good])
            # One axis frame within each session avoids misleading zoom changes.
            xmin, xmax = float(joined[:, 0].min()), float(joined[:, 0].max())
            ymin, ymax = float(joined[:, 1].min()), float(joined[:, 1].max())
            margin = max((xmax-xmin), (ymax-ymin), .1)*.10
        for col, result in enumerate(results):
            ax = axs[r, col]
            render_network(ax, result.metric, result.xy, result.shown, result.parties, PARTY_COLORS)
            if result.metric.status == 'ok':
                ax.set_xlim(xmin-margin, xmax+margin)
                ax.set_ylim(ymin-margin, ymax+margin)
                ax.set_aspect('equal', adjustable='box')
    present = {p for row in all_results.values() for result in row for p in result.parties}
    markers = [plt.Line2D([0], [0], marker='o', linestyle='', color=PARTY_COLORS[p],
                          label=p, markersize=6) for p in PARTY_ORDER if p in present]
    fig.suptitle(title, fontsize=15)
    if markers:
        fig.legend(handles=markers, loc='lower center', ncol=min(6,len(markers)),
                   frameon=False, bbox_to_anchor=(.5, .045), fontsize=8)
    fig.text(.5, .014, 'Layouts stabilized on common MP IDs for display only. '
             'Quarters use equal numbers of recorded divisions; distances are not ideological units.',
             ha='center', fontsize=8)
    fig.tight_layout(rect=(0, .09, 1, .96), w_pad=1.0, h_pad=2.0)
    fig.savefig(path, dpi=170, bbox_inches='tight')
    plt.close(fig)


def save_quarterly_trends(records: list[dict], sessions: list[str], path: Path) -> None:
    fig, axs = plt.subplots(len(sessions), 1, figsize=(12, 4*len(sessions)), squeeze=False)
    for ax, session in zip(axs.flat, sessions):
        rows = sorted((r for r in records if r['session'] == session and r['mode'] == 'independent'),
                      key=lambda r: r['index'])
        for metric, color, label in [('mean_same','#2e6d9f','Within-party'),
                                      ('mean_cross','#cf5359','Cross-party')]:
            x = [r['index'] for r in rows if r['status']=='ok' and r[metric] is not None]
            y = [r[metric]*100 for r in rows if r['status']=='ok' and r[metric] is not None]
            ax.plot(x, y, 'o-', color=color, linewidth=2, label=label)
        ax.set_title(f'{session}: independent quarters')
        ax.set_xticks(range(1,5), [f'Q{i}' for i in range(1,5)])
        ax.set_ylabel('Mean MP-pair voting agreement (%)')
        ax.set_ylim(0, 100)
        ax.grid(alpha=.2)
        ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(path, dpi=175)
    plt.close(fig)


def save_rolling_trends(records: list[dict], sessions: list[str], path: Path) -> None:
    fig, axs = plt.subplots(len(sessions), 1, figsize=(12, 4*len(sessions)), squeeze=False)
    for ax, session in zip(axs.flat, sessions):
        rows = sorted((r for r in records if r['session'] == session and r['mode'] == 'rolling'),
                      key=lambda r: r['index'])
        for metric, color, label in [('mean_same','#2e6d9f','Within-party'),
                                      ('mean_cross','#cf5359','Cross-party')]:
            vals = [(r['end_fraction']*100, r[metric]*100) for r in rows
                    if r['status']=='ok' and r[metric] is not None]
            if vals:
                x, y = zip(*vals)
                ax.plot(x, y, '-', color=color, linewidth=1.8, label=label)
        ax.set_title(f'{session}: trailing {rows[0]["divisions"] if rows else "?"}-division windows')
        ax.set_ylabel('Pair agreement (%)')
        ax.set_xlabel('Session progress measured by recorded divisions (%)')
        ax.set_ylim(0, 100)
        ax.set_xlim(0, 100)
        ax.grid(alpha=.2)
        ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(path, dpi=175)
    plt.close(fig)


def save_rolling_party_pairs(records: list[dict], sessions: list[str], path: Path) -> None:
    targets = [('Liberal','Conservative'), ('Liberal','NDP'), ('Conservative','NDP')]
    fig, axs = plt.subplots(len(sessions), 1, figsize=(12, 4*len(sessions)), squeeze=False)
    for ax, session in zip(axs.flat, sessions):
        rows = [r for r in records if r['session'] == session and r['mode'] == 'rolling']
        for party_a, party_b in targets:
            a,b = sorted((party_a,party_b))
            pts = sorted([(r['end_fraction']*100, r['mean_agreement']*100)
                           for r in rows if r['party_a']==a and r['party_b']==b],
                          key=lambda pair:pair[0])
            if pts:
                x, y = zip(*pts)
                ax.plot(x, y, linewidth=2, label=f'{party_a}–{party_b}')
        ax.set_title(f'{session}: rolling cross-party voting relationships')
        ax.set_xlabel('Session progress by recorded divisions (%)')
        ax.set_ylabel('Mean pair agreement (%)')
        ax.set_xlim(0, 100)
        ax.set_ylim(0, 100)
        ax.grid(alpha=.2)
        ax.legend(frameon=False, ncol=3, loc='upper center')
    fig.tight_layout()
    fig.savefig(path, dpi=175)
    plt.close(fig)


def run(args) -> None:
    """Entry point using validated args from network_partisanship.main()."""
    sessions = list(args.sessions) if not args.all else list(__import__('check_data').SESSIONS)
    if not args.skip_validation:
        from check_data import require_valid_corpus
        require_valid_corpus(sessions=sessions)
    if args.rolling_width < 2 or args.rolling_step < 1 or args.min_window_divisions < 2:
        raise ValueError('rolling width >=2, step >=1 and min-window-divisions >=2 required')
    args.output.mkdir(parents=True, exist_ok=False)
    rows, pair_rows, correspondence_rows, profile_rows, movement_rows = [], [], [], [], []
    independent_atlas, cumulative_atlas = {}, {}
    for session in sessions:
        corpus = load_corpus(session, args.category)
        n = len(corpus.divisions)
        groups = [('independent', quarter_windows(n)),
                  ('cumulative', cumulative_windows(n)),
                  ('rolling', rolling_windows(n, args.rolling_width, args.rolling_step))]
        for mode, windows in groups:
            results = []
            prev_profile = []
            for window in windows:
                result = evaluate(corpus, window, threshold=args.threshold,
                                  min_common=args.min_common,
                                  min_window_divisions=args.min_window_divisions,
                                  selected_parties=args.parties,
                                  draw=(mode != 'rolling'), seed=args.seed)
                results.append(result)
                m = result.metric
                record = dict(session=session, mode=mode, window=window.label,
                              index=window.index, start_index=window.start,
                              end_index=window.end, divisions=window.end-window.start,
                              start_fraction=window.start/n if n else 0,
                              end_fraction=window.end/n if n else 0,
                              first_division=corpus.divisions[window.start] if window.start<n else '',
                              last_division=corpus.divisions[window.end-1] if window.end>window.start else '',
                              first_date=corpus.dates[window.start] if window.start<n else '',
                              last_date=corpus.dates[window.end-1] if window.end>window.start else '',
                              **{k:v for k,v in asdict(m).items() if k not in ('session','divisions')})
                rows.append(record)
                for (a,b), (count,mean,median) in sorted(result.pair_summary.items()):
                    pair_rows.append(dict(session=session,mode=mode,window=window.label,
                                          index=window.index,end_fraction=record['end_fraction'],
                                          party_a=a,party_b=b,pairs=count,
                                          mean_agreement=mean, median_agreement=median))
                if mode == 'independent':
                    profile = party_profiles(result, args.min_common) if m.status=='ok' else []
                    for item in profile:
                        profile_rows.append(dict(session=session,**item))
                    if prev_profile and profile:
                        movement_rows.extend(dict(session=session, **r) for r in profile_change(prev_profile, profile))
                    prev_profile = profile
                if len(results)>1 and mode != 'rolling':
                    correspondence_rows.append(dict(session=session,mode=mode,
                         from_window=results[-2].window.label,to_window=window.label,
                         **adjacency_correspondence(results[-2],result,args.min_common)))
                print(f'{session} {mode} {window.label}: {record["divisions"]} votes; '
                      f'status={m.status}; same={m.mean_same} cross={m.mean_cross}', flush=True)
            if mode=='independent':
                independent_atlas[session]=results
            if mode=='cumulative':
                cumulative_atlas[session]=results
    metric_columns = ['session','mode','window','index','start_index','end_index','divisions',
                      'start_fraction','end_fraction','first_division','last_division','first_date','last_date'] + \
                     [k for k in Period.__dataclass_fields__ if k not in ('session','divisions')]
    export_csv(args.output/'temporal_metrics.csv',rows,metric_columns)
    export_csv(args.output/'temporal_party_pairs.csv',pair_rows,
               ['session','mode','window','index','end_fraction','party_a','party_b','pairs','mean_agreement','median_agreement'])
    export_csv(args.output/'quarter_correspondence.csv',correspondence_rows,
               ['session','mode','from_window','to_window','common_mps','comparable_pairs',
                'agreement_correlation','edge_jaccard','edges_gained','edges_lost'])
    export_csv(args.output/'mp_party_affinities.csv',profile_rows,
               ['session','member_id','party','votes_cast','window','mode']+list(PARTY_ORDER))
    export_csv(args.output/'mp_affinity_changes.csv',movement_rows,
               ['session','member_id','previous_window','current_window','from_party','to_party',
                'affiliation_changed','common_party_dimensions','rms_party_affinity_change',
                'max_abs_party_affinity_change'])
    save_atlas(independent_atlas,args.output/'quarterly_networks.png',
               'Independent-quarter voting networks: Canadian House of Commons')
    save_atlas(cumulative_atlas,args.output/'cumulative_networks.png',
               'Cumulative-quarter voting networks: Canadian House of Commons')
    save_quarterly_trends(rows,sessions,args.output/'quarterly_agreement.png')
    save_rolling_trends(rows,sessions,args.output/'rolling_agreement.png')
    save_rolling_party_pairs(pair_rows,sessions,args.output/'rolling_party_pairs.png')
    (args.output/'manifest.json').write_text(json.dumps({
        'schema_version':1,'sessions':sessions,'mode':'quarterly + cumulative + rolling',
        'category':args.category,'min_common':args.min_common,
        'min_window_divisions':args.min_window_divisions,'rolling_width':args.rolling_width,
        'rolling_step':args.rolling_step,'threshold':args.threshold,'parties':args.parties,
        'seed':args.seed,'division_order':'numeric division number',
        'quarter_definition':'equal observed division counts, not equal calendar duration',
        'source':'Validated source files in MyWolve/Party-Partisanship',
        'warning':'All values are descriptive; votes and issue types are not independently sampled. '
                  'Overlapping rolling and cumulative windows are dependent. '
                  'Plot positions are orientation-aligned only, not standardized ideological coordinates. '
                  '45-1 is incomplete; 40-1 and 43-1 have few recorded divisions.'
    }, indent=2)+'\n',encoding='utf-8')
    print(f'Temporal analysis written to {args.output}',flush=True)
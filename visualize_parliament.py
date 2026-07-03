"""
Analyze and visualize party voting cohesion in the Canadian House of Commons.

Two cohesion metrics are available:

  "majority"  -- share of the party's votes cast on the party's majority side.
                 Ranges from 50 to 100.

  "rice"      -- the Rice Index: |yea - nay| / (yea + nay) * 100.
                 Ranges from 0 (perfect split) to 100 (unanimous). This is the
                 standard cohesion measure that I could find in the political science literature,
                 so results are directly comparable to published work.

Members who did not vote Yea or Nay (e.g. paired members) are excluded from
both metrics. A party with no votes cast on a division gets a score of None,
and None values are excluded from averages.
"""

import os
import re
import csv
import random
import matplotlib.pyplot as plt

# Project root = the directory this script lives in
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

PARTIES = ["Conservative", "Liberal", "NDP", "Bloc Québécois", "Green Party", "Independent"]

# To track another party, add one line here.
PARTY_COLORS = {
    "Conservative": "#1C4857",
    "Liberal": "#D71920",
    "NDP": "#F58220",
    "Bloc Québécois": "#33B2CC",
    "Green Party": "#3D9B35",
    "Independent": "#777777"
}

# Affiliations that appear in the data but aren't tracked in PARTIES
# are listed as "Independent". The below can be used to track certain
# small affiliations explicitly. For example:
#   Independent Conservative, Conservative Independent, Forces et Démocratie,
#   People's Party, etc.
AFFILIATION_ALIASES = {
    "Independent Conservative": "Independent",       # Goldring, Guergis (40-3, 41-1)
    "Conservative Independent": "Independent",       # Del Mastro (41-2)
    "Co-operative Commonwealth Federation": "Independent",  # Weir, ex-NDP (42-1)
    "Québec debout": "Independent",                  # ex-Bloc caucus split (42-1)
    "Forces et Démocratie": "Independent",           # Fortin, Larose (41-2)
    "People's Party": "Independent",                 # Bernier (42-1)
}

# ----------------------------------------------------------------------
# Data Loading
# ----------------------------------------------------------------------

def _find_column(header, *fragments, default=None):
    """Locate a column index by substring match on the header (case-insensitive)."""
    for index, name in enumerate(header):
        lowered = name.lower()
        if any(fragment in lowered for fragment in fragments):
            return index
    return default


def read_vote_rows(file_path):
    """Read one vote CSV into [{"member", "party", "vote", "paired"}, ...].

    Column positions are located from the header row, because the House's
    export format has changed over time: older files are
    (Member, Affiliation, Voted, Paired) while the current endpoint
    prepends a Person ID column. Reading by header name handles both,
    plus any future reshuffle. Falls back to the legacy positions if the
    header is unrecognizable.
    """
    with open(file_path, "r", encoding="utf-8-sig", errors="ignore") as file:
        reader = csv.reader(file)
        header = next(reader, None)
        if header is None:
            return []

        member_col = _find_column(header, "member of parliament", default=0)
        party_col = _find_column(header, "affiliation", "political party",
                                 default=1)
        vote_col = _find_column(header, "voted", "member voted", default=2)
        paired_col = _find_column(header, "paired", default=3)

        rows = []
        for row in reader:
            if len(row) <= vote_col:
                continue
            rows.append({
                "member": row[member_col],
                "party": row[party_col],
                "vote": row[vote_col],
                "paired": (len(row) > paired_col
                           and row[paired_col].strip() == "Paired"),
            })
        return rows


def load_vote_file(file_path):
    """
    Read one vote CSV and return {party: [(member, vote), ...]}.

    Any affiliation not in PARTIES is grouped under "Independent".
    """
    votes = {party: [] for party in PARTIES}

    for row in read_vote_rows(file_path):
        affiliation = AFFILIATION_ALIASES.get(row["party"], row["party"])
        party = affiliation if affiliation in PARTIES else "Independent"
        votes[party].append((row["member"], row["vote"]))

    return votes

def load_parliament(directory, bill=None):
    """
    Load vote data for a parliament session directory.

    If bill is given (e.g. "file_23.csv"), returns a single
    {party: [(member, vote), ...]} dict for that vote.

    Otherwise returns a list of (bill_name, votes_dict) for every vote in the
    directory, sorted by vote number.
    """
    if bill is not None:
        for filename in os.listdir(directory):
            if bill in filename:
                return load_vote_file(os.path.join(directory, filename))
        raise FileNotFoundError(f"No file matching '{bill}' in {directory}")

    bills = []
    for filename in os.listdir(directory):
        file_path = os.path.join(directory, filename)
        # Only file_<N>.csv vote files; the directory may also contain
        # votes_metadata.csv (see bill_info.py), which is not a division.
        if (os.path.isfile(file_path)
                and re.fullmatch(r"file_\d+\.csv", filename)):
            bill_name = os.path.splitext(filename)[0]  # e.g. "file_23"
            bills.append((bill_name, load_vote_file(file_path)))

    bills.sort(key=lambda item: vote_number(item[0]))
    return bills

def vote_number(bill_name):
    """Extract the vote number from a bill file name like 'file_23'."""
    return int(bill_name.split("_")[1])

# ----------------------------------------------------------------------
# Cohesion Metrics
# ----------------------------------------------------------------------

def count_yea_nay(member_votes):
    """Count Yea and Nay votes in a list of (member, vote) tuples."""
    yea = sum(1 for _, vote in member_votes if vote == "Yea")
    nay = sum(1 for _, vote in member_votes if vote == "Nay")
    return yea, nay


def majority_cohesion(member_votes):
    """
    Share of votes cast on the majority side, as a percentage (50-100).

    Returns None if the party cast no Yea/Nay votes on this division.
    """
    yea, nay = count_yea_nay(member_votes)
    total = yea + nay
    if total == 0:
        return None
    return round(max(yea, nay) / total * 100, 2)

def rice_index(member_votes):
    """
    Rice Index of cohesion: |yea - nay| / (yea + nay) * 100 (0-100).

    Returns None if the party cast no Yea/Nay votes on this division.
    """
    yea, nay = count_yea_nay(member_votes)
    total = yea + nay
    if total == 0:
        return None
    return round(abs(yea - nay) / total * 100, 2)


METRICS = {
    "majority": majority_cohesion,
    "rice": rice_index,
}


def cohesion_by_party(votes, metric="rice"):
    """
    Compute cohesion for every party on a single vote.

    Returns {party: score or None}.
    """
    score = METRICS[metric]
    return {party: score(votes[party]) for party in PARTIES}


def average_cohesion(bills, metric="rice"):
    """
    Average each party's cohesion across all bills, ignoring None values.

    Returns {party: average score or None if the party never voted}.
    """
    totals = {party: 0.0 for party in PARTIES}
    counts = {party: 0 for party in PARTIES}

    for _, votes in bills:
        scores = cohesion_by_party(votes, metric)
        for party, value in scores.items():
            if value is not None:
                totals[party] += value
                counts[party] += 1

    return {
        party: round(totals[party] / counts[party], 2) if counts[party] else None
        for party in PARTIES
    }


def print_cohesion(votes, metric="rice"):
    """Print each party's cohesion and vote breakdown for a single vote."""
    scores = cohesion_by_party(votes, metric)
    print(f"\nCohesion ({metric} metric):")
    for party in PARTIES:
        yea, nay = count_yea_nay(votes[party])
        score = scores[party]
        score_text = f"{score}%" if score is not None else "N/A"
        print(f"  {party}: {score_text} (Yea: {yea}, Nay: {nay})")

# ----------------------------------------------------------------------
# Plotting
# ----------------------------------------------------------------------

def plot_cohesion_bar(party_cohesion, title="Party Cohesion", save_path=None):
    """Bar chart of one cohesion score per party. None values are skipped."""
    plotted = {p: v for p, v in party_cohesion.items() if v is not None}

    plt.figure(figsize=(10, 6))
    parties = list(plotted.keys())
    values = list(plotted.values())
    colors = [PARTY_COLORS[p] for p in parties]

    plt.bar(parties, values, color=colors)
    plt.xlabel("Parties")
    plt.ylabel("Cohesion (%)")
    plt.title(title)
    plt.ylim(0, 105)

    for i, value in enumerate(values):
        plt.text(i, value + 1, f"{value}%", ha="center")

    if save_path:
        plt.savefig(save_path)
        plt.close()
    else:
        plt.show()


def plot_cohesion_over_time(directory, metric="rice", excluded_parties=None,save_path=None):
    """Line plot of each party's cohesion across every vote in a session."""
    if excluded_parties is None:
        excluded_parties = []

    bills = load_parliament(directory)
    included = [p for p in PARTIES if p not in excluded_parties]

    # scores[party] is a list parallel to bill_numbers; None where no votes.
    bill_numbers = [vote_number(name) for name, _ in bills]
    scores = {party: [] for party in included}
    for _, votes in bills:
        bill_scores = cohesion_by_party(votes, metric)
        for party in included:
            scores[party].append(bill_scores[party])

    plt.figure(figsize=(20, 10))
    for party in included:
        # Skip votes where the party has no score so lines don't drop to zero.
        points = [(n, s) for n, s in zip(bill_numbers, scores[party])
                  if s is not None]
        if not points:
            continue
        xs, ys = zip(*points)
        plt.plot(xs, ys, label=party, color=PARTY_COLORS[party],
                 marker="o", linestyle="-", markersize=6, alpha=0.5)

    session = os.path.basename(os.path.normpath(directory))
    plt.xlabel("Vote number")
    plt.ylabel(f"Cohesion (%) — {metric} metric")
    plt.title(f"Party Cohesion: {session}")
    plt.grid(True, linestyle="--", alpha=0.7)
    plt.legend()
    plt.tight_layout(pad=3)

    if save_path:
        plt.savefig(save_path)
        plt.close()
    else:
        plt.show()

# ----------------------------------------------------------------------
# Dissent Analysis
# 
# In a legislature as 'disciplined' as the Canadian HOCm average cohesions
# scores are consistently high and no longer discriminate results. The more
# informative statistics then perhaps are: how OFTEN does any dissent occur,
# WHO are the rebels, and on WHICH votes. A "rebel" is a Member of Parliament (MP)
# who cast a Yea/Nay vote against their party's majority side on that decision. 
# Decisions where a party is tied, or cast no votes, are skipped for that party.
# 
# The Independent group is excluded by default: it has no whip, so "dissent"
# is necessarily meaningless for them.  
# ----------------------------------------------------------------------

import bill_info

WHIPPED_PARTIES = [p for p in PARTIES if p != "Independent"]
 
 
def party_majority_side(member_votes):
    """
    Return 'Yea' or 'Nay' for the party's majority side, or None on a
    tie / no votes (in which case rebellion is undefined for this division).
    """
    yea, nay = count_yea_nay(member_votes)
    if yea == nay:
        return None
    return "Yea" if yea > nay else "Nay"
 
 
def find_rebels(votes, parties=None):
    """
    Identify rebels on a single division.
 
    Returns {party: [member, ...]} listing MPs who voted against their
    party's majority side. Parties with a tie or no votes map to None
    (undefined) rather than an empty list, so callers can tell
    "no rebellion" apart from "rebellion undefined".
    """
    if parties is None:
        parties = WHIPPED_PARTIES
 
    rebels = {}
    for party in parties:
        majority = party_majority_side(votes[party])
        if majority is None:
            rebels[party] = None
            continue
        rebels[party] = [
            member for member, vote in votes[party]
            if vote in ("Yea", "Nay") and vote != majority
        ]
    return rebels
 
 
def dissent_summary(bills, parties=None):
    """
    Summarize dissent across all divisions in a session.
 
    Returns {party: {"divisions": int,        # divisions with a defined majority
                     "with_dissent": int,     # divisions with >= 1 rebel
                     "dissent_rate": float,   # percentage of the above
                     "total_rebel_votes": int,
                     "largest_rebellion": (bill_name, rebel_count) or None}}
    """
    if parties is None:
        parties = WHIPPED_PARTIES
 
    summary = {
        party: {"divisions": 0, "with_dissent": 0, "total_rebel_votes": 0,
                "largest_rebellion": None}
        for party in parties
    }
 
    for bill_name, votes in bills:
        rebels = find_rebels(votes, parties)
        for party in parties:
            party_rebels = rebels[party]
            if party_rebels is None:
                continue
            stats = summary[party]
            stats["divisions"] += 1
            if party_rebels:
                stats["with_dissent"] += 1
                stats["total_rebel_votes"] += len(party_rebels)
                largest = stats["largest_rebellion"]
                if largest is None or len(party_rebels) > largest[1]:
                    stats["largest_rebellion"] = (bill_name, len(party_rebels))
 
    for stats in summary.values():
        stats["dissent_rate"] = (
            round(stats["with_dissent"] / stats["divisions"] * 100, 2)
            if stats["divisions"] else None
        )
    return summary
 
 
def mp_loyalty(bills, parties=None, min_votes=10):
    """
    Compute per-MP loyalty across a session.
 
    Loyalty = share of an MP's Yea/Nay votes cast with their party's
    majority side (affiliation is taken per-division, so floor-crossers are
    scored against whichever party they belonged to at the time). MPs with
    fewer than min_votes qualifying votes are excluded to avoid noisy
    percentages from tiny denominators.
 
    Returns {member: {"party": most common party, "votes": int,
                      "rebellions": int, "loyalty": float,
                      "rebel_bills": [bill_name, ...]}}
    sorted by rebellion count (most rebellious first).
    """
    if parties is None:
        parties = WHIPPED_PARTIES
 
    records = {}  # member -> {"parties": {party: count}, "votes", "rebellions", "rebel_bills"}
 
    for bill_name, votes in bills:
        for party in parties:
            majority = party_majority_side(votes[party])
            if majority is None:
                continue
            for member, vote in votes[party]:
                if vote not in ("Yea", "Nay"):
                    continue
                record = records.setdefault(
                    member, {"parties": {}, "votes": 0, "rebellions": 0,
                             "rebel_bills": []})
                record["parties"][party] = record["parties"].get(party, 0) + 1
                record["votes"] += 1
                if vote != majority:
                    record["rebellions"] += 1
                    record["rebel_bills"].append(bill_name)
 
    result = {}
    for member, record in records.items():
        if record["votes"] < min_votes:
            continue
        main_party = max(record["parties"], key=record["parties"].get)
        result[member] = {
            "party": main_party,
            "votes": record["votes"],
            "rebellions": record["rebellions"],
            "loyalty": round(
                (record["votes"] - record["rebellions"]) / record["votes"] * 100, 2),
            "rebel_bills": record["rebel_bills"],
        }
 
    return dict(sorted(result.items(),
                       key=lambda item: item[1]["rebellions"], reverse=True))
 
 
def print_dissent_report(directory, parties=None, top_n=10):
    """Print a dissent summary and the top rebel MPs for a session."""
    bills = load_parliament(directory)
    session = os.path.basename(os.path.normpath(directory))
    summary = dissent_summary(bills, parties)
    loyalty = mp_loyalty(bills, parties)
 
    print(f"\nDissent report: {session} ({len(bills)} divisions)")
    print("-" * 72)
    for party, stats in summary.items():
        if not stats["divisions"]:
            continue
        largest = stats["largest_rebellion"]
        largest_text = (f"largest: {largest[1]} rebels on vote "
                        f"{vote_number(largest[0])}" if largest else "largest: -")
        print(f"  {party}: dissent on {stats['with_dissent']}/{stats['divisions']} "
              f"divisions ({stats['dissent_rate']}%), "
              f"{stats['total_rebel_votes']} rebel votes total, {largest_text}")
 
    print(f"\n  Top {top_n} rebels (min. 10 votes cast):")
    for member, record in list(loyalty.items())[:top_n]:
        if record["rebellions"] == 0:
            break
        print(f"    {member} [{record['party']}]: "
              f"{record['rebellions']} rebellions in {record['votes']} votes "
              f"(loyalty {record['loyalty']}%)")
    return summary, loyalty
 
 
def plot_dissent_rate(directory, parties=None, save_path=None):
    """Bar chart: percentage of divisions with at least one rebel, per party."""
    bills = load_parliament(directory)
    summary = dissent_summary(bills, parties)
    session = os.path.basename(os.path.normpath(directory))
 
    plotted = {p: s["dissent_rate"] for p, s in summary.items()
               if s["dissent_rate"] is not None}
 
    plt.figure(figsize=(10, 6))
    names = list(plotted.keys())
    values = list(plotted.values())
    plt.bar(names, values, color=[PARTY_COLORS[p] for p in names])
    plt.xlabel("Party")
    plt.ylabel("Divisions with any dissent (%)")
    plt.title(f"Dissent Frequency: {session}")
    for i, value in enumerate(values):
        plt.text(i, value + 0.3, f"{value}%", ha="center")
 
    if save_path:
        plt.savefig(save_path)
        plt.close()
    else:
        plt.show()
 
 
def plot_rebellions_over_time(directory, parties=None, save_path=None):
    """
    Scatter of rebel counts per division, showing only nonzero rebellions.
 
    In a disciplined House most divisions have zero rebels, so plotting only
    the exceptions makes the interesting votes (free votes, conscience
    issues, caucus crises) stand out immediately.
    """
    if parties is None:
        parties = WHIPPED_PARTIES
 
    bills = load_parliament(directory)
    session = os.path.basename(os.path.normpath(directory))
 
    plt.figure(figsize=(20, 8))
    for party in parties:
        xs, ys = [], []
        for bill_name, votes in bills:
            rebels = find_rebels(votes, [party])[party]
            if rebels:
                xs.append(vote_number(bill_name))
                ys.append(len(rebels))
        if xs:
            plt.scatter(xs, ys, label=party, color=PARTY_COLORS[party],
                        s=45, alpha=0.7)
 
    plt.xlabel("Vote number")
    plt.ylabel("Number of rebels")
    plt.title(f"Rebellions by Division: {session} "
              f"(divisions with zero rebels omitted)")
    plt.grid(True, linestyle="--", alpha=0.5)
    plt.legend()
    plt.tight_layout()
 
    if save_path:
        plt.savefig(save_path)
        plt.close()
    else:
        plt.show()
 
 
def plot_top_rebels(directory, parties=None, top_n=15, save_path=None):
    """Horizontal bar chart of the MPs with the most rebellions in a session."""
    bills = load_parliament(directory)
    loyalty = mp_loyalty(bills, parties)
    session = os.path.basename(os.path.normpath(directory))
 
    top = [(m, r) for m, r in loyalty.items() if r["rebellions"] > 0][:top_n]
    if not top:
        print(f"No rebellions found in {session}.")
        return
    top.reverse()  # largest at the top of the chart
 
    names = [f"{m.split('(')[0].strip()} [{r['party']}]" for m, r in top]
    values = [r["rebellions"] for _, r in top]
    colors = [PARTY_COLORS[r["party"]] for _, r in top]
 
    plt.figure(figsize=(12, max(4, 0.45 * len(top))))
    plt.barh(names, values, color=colors)
    plt.xlabel("Rebellions (votes against party majority)")
    plt.title(f"Most Rebellious MPs: {session}")
    for i, (value, (_, record)) in enumerate(zip(values, top)):
        plt.text(value + 0.1, i, f"{value} ({record['loyalty']}% loyal)",
                 va="center", fontsize=9)
    plt.tight_layout()
 
    if save_path:
        plt.savefig(save_path)
        plt.close()
    else:
        plt.show()


# ----------------------------------------------------------------------
# Dissent by vote category (requires votes_metadata.csv; see bill_info.py)
#
# This is the direct test of the whip: if party discipline is doing the
# work, dissent should concentrate almost entirely in private members'
# business (traditionally unwhipped) and be near zero on government
# bills and confidence matters.
# ----------------------------------------------------------------------

def dissent_by_category(directory, parties=None):
    """
    Cross-tabulate dissent by party and vote category.

    Returns {party: {category: {"divisions", "with_dissent", "dissent_rate",
                                "total_rebel_votes"}}}.
    Raises FileNotFoundError if the session has no votes_metadata.csv.
    """
    if parties is None:
        parties = WHIPPED_PARTIES

    metadata = bill_info.load_vote_metadata(directory)
    if not metadata:
        raise FileNotFoundError(
            f"No votes_metadata.csv in {directory}; run the scraper's "
            f"metadata step first (see can_scrape.py).")

    bills = load_parliament(directory)
    table = {party: {} for party in parties}

    for bill_name, votes in bills:
        number = vote_number(bill_name)
        if number not in metadata:
            continue
        category = metadata[number]["category"]
        rebels = find_rebels(votes, parties)
        for party in parties:
            party_rebels = rebels[party]
            if party_rebels is None:
                continue
            cell = table[party].setdefault(
                category, {"divisions": 0, "with_dissent": 0,
                           "total_rebel_votes": 0})
            cell["divisions"] += 1
            if party_rebels:
                cell["with_dissent"] += 1
                cell["total_rebel_votes"] += len(party_rebels)

    for party_cells in table.values():
        for cell in party_cells.values():
            cell["dissent_rate"] = round(
                cell["with_dissent"] / cell["divisions"] * 100, 2)
    return table


def mp_loyalty_split(directory, parties=None, min_votes=10,
                     free_categories=None):
    """
    Per-MP loyalty computed separately for whipped and free business.

    An MP at 99% whipped / 75% free is a conscientious backbencher who
    respects the whip; one rebelling on whipped business is a different
    animal entirely. Returns
    {member: {"party", "whipped": {"votes", "rebellions", "loyalty"},
              "free": {...}}}
    sorted by whipped-business rebellions.
    """
    if parties is None:
        parties = WHIPPED_PARTIES
    if free_categories is None:
        free_categories = bill_info.FREE_VOTE_CATEGORIES

    metadata = bill_info.load_vote_metadata(directory)
    if not metadata:
        raise FileNotFoundError(f"No votes_metadata.csv in {directory}.")

    bills = load_parliament(directory)
    records = {}

    for bill_name, votes in bills:
        number = vote_number(bill_name)
        if number not in metadata:
            continue
        bucket = ("free" if metadata[number]["category"] in free_categories
                  else "whipped")
        for party in parties:
            majority = party_majority_side(votes[party])
            if majority is None:
                continue
            for member, vote in votes[party]:
                if vote not in ("Yea", "Nay"):
                    continue
                record = records.setdefault(member, {
                    "parties": {},
                    "whipped": {"votes": 0, "rebellions": 0},
                    "free": {"votes": 0, "rebellions": 0}})
                record["parties"][party] = record["parties"].get(party, 0) + 1
                record[bucket]["votes"] += 1
                if vote != majority:
                    record[bucket]["rebellions"] += 1

    result = {}
    for member, record in records.items():
        total = record["whipped"]["votes"] + record["free"]["votes"]
        if total < min_votes:
            continue
        entry = {"party": max(record["parties"], key=record["parties"].get)}
        for bucket in ("whipped", "free"):
            votes_cast = record[bucket]["votes"]
            rebellions = record[bucket]["rebellions"]
            entry[bucket] = {
                "votes": votes_cast,
                "rebellions": rebellions,
                "loyalty": (round((votes_cast - rebellions) / votes_cast * 100, 2)
                            if votes_cast else None),
            }
        result[member] = entry

    return dict(sorted(result.items(),
                       key=lambda item: item[1]["whipped"]["rebellions"],
                       reverse=True))


def print_whip_report(directory, parties=None, top_n=10):
    """The whip test: dissent rates by category, plus split loyalty."""
    session = os.path.basename(os.path.normpath(directory))
    table = dissent_by_category(directory, parties)
    loyalty = mp_loyalty_split(directory, parties)

    print(f"\nWhip report: {session}")
    print("-" * 72)
    for party, cells in table.items():
        if not cells:
            continue
        print(f"  {party}:")
        for category, cell in sorted(cells.items(),
                                     key=lambda c: -c[1]["dissent_rate"]):
            print(f"    {category}: {cell['with_dissent']}/{cell['divisions']} "
                  f"divisions with dissent ({cell['dissent_rate']}%), "
                  f"{cell['total_rebel_votes']} rebel votes")

    print(f"\n  Top {top_n} whipped-business rebels:")
    shown = 0
    for member, record in loyalty.items():
        if record["whipped"]["rebellions"] == 0 or shown >= top_n:
            break
        free = record["free"]
        free_text = (f"free loyalty {free['loyalty']}% ({free['votes']} votes)"
                     if free["votes"] else "no free votes")
        print(f"    {member} [{record['party']}]: "
              f"{record['whipped']['rebellions']} whipped rebellions "
              f"(loyalty {record['whipped']['loyalty']}%), {free_text}")
        shown += 1
    return table, loyalty


def plot_dissent_by_category(directory, parties=None, save_path=None):
    """Grouped bar chart: dissent rate per category, one bar group per party."""
    table = dissent_by_category(directory, parties)
    session = os.path.basename(os.path.normpath(directory))

    categories = sorted({c for cells in table.values() for c in cells})
    party_names = [p for p in table if table[p]]

    plt.figure(figsize=(14, 7))
    width = 0.8 / max(len(party_names), 1)
    for i, party in enumerate(party_names):
        xs = [j + i * width for j in range(len(categories))]
        ys = [table[party].get(c, {}).get("dissent_rate", 0)
              for c in categories]
        plt.bar(xs, ys, width=width, label=party, color=PARTY_COLORS[party])

    plt.xticks([j + width * (len(party_names) - 1) / 2
                for j in range(len(categories))],
               [c.replace("_", "\n") for c in categories])
    plt.ylabel("Divisions with any dissent (%)")
    plt.title(f"Dissent Rate by Vote Category: {session}")
    plt.legend()
    plt.tight_layout()

    if save_path:
        plt.savefig(save_path)
        plt.close()
    else:
        plt.show()


# ----------------------------------------------------------------------
# Convenience entry points
# ----------------------------------------------------------------------

def parliament_directories():
    """List all Parliament_* directories in the project root."""
    return sorted(
        os.path.join(PROJECT_ROOT, d)
        for d in os.listdir(PROJECT_ROOT)
        if d.startswith("Parliament_") and os.path.isdir(os.path.join(PROJECT_ROOT, d))
    )
 
 
def analyze_bill(directory, bill, metric="rice"):
    """Print and plot cohesion for a single vote."""
    votes = load_parliament(directory, bill)
    print(f"Parliament: {directory}")
    print(f"Bill: {bill}")
    print_cohesion(votes, metric)
    plot_cohesion_bar(cohesion_by_party(votes, metric),
                      title=f"Party Cohesion: {bill} ({metric})")
 
 
def analyze_parliament(directory, metric="rice"):
    """Print and plot average cohesion across every vote in a session."""
    bills = load_parliament(directory)
    averages = average_cohesion(bills, metric)
    session = os.path.basename(os.path.normpath(directory))
    print(f"\nAverage cohesion for {session} across {len(bills)} votes "
          f"({metric} metric):")
    for party in PARTIES:
        value = averages[party]
        print(f"  {party}: {value if value is not None else 'N/A'}")
    plot_cohesion_bar(averages, title=f"Average Party Cohesion: {session} ({metric})")
 
 
def analyze_random_bill(metric="rice"):
    """Pick a random session and vote, then analyze it."""
    directory = random.choice(parliament_directories())
    bill = random.choice([f for f in os.listdir(directory) if f.endswith(".csv")])
    analyze_bill(directory, bill, metric)
 
 
def analyze_dissent(directory, top_n=15):
    """Full dissent workup for a session: report plus all three plots."""
    session = os.path.basename(os.path.normpath(directory))
    print_dissent_report(directory, top_n=top_n)
    plot_dissent_rate(directory, save_path=f"dissent_rate_{session}.png")
    plot_rebellions_over_time(
        directory, save_path=f"rebellions_over_time_{session}.png")
    plot_top_rebels(directory, top_n=top_n,
                    save_path=f"top_rebels_{session}.png")
    print(f"\nSaved dissent_rate_{session}.png, "
          f"rebellions_over_time_{session}.png, top_rebels_{session}.png")
 
 
if __name__ == "__main__":
    directory = random.choice(parliament_directories())
    plot_cohesion_over_time(directory, metric="rice",
                            excluded_parties=["Independent"],
                            save_path="cohesion_by_bill_sorted.png")
    print(f"Saved cohesion_by_bill_sorted.png for {directory}")
    analyze_dissent(directory)
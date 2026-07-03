"""Experiment 1: The whip test.

Are Whips that successful? If party discipline is doing the work, dissent
should concentrate almost entirely where the whip is off. The cleanest
comparison is the GOVERNING party's dissent rate on government bills
versus private members' business: the same caucus under two whip
conditions, controlling for party culture.

For every session this script computes, per party and per vote category:
the number of divisions, the number with at least one rebel, and the
dissent rate. It reports:

  1. The headline: governing-party dissent on government bills vs.
     private members' business, per session and pooled.
  2. A robustness variant excluding near-unanimous divisions (where more
     than UNANIMITY_THRESHOLD of the whole House voted the same way).
  3. The largest governing-party rebellions on government bills, for
     manual spot-checking: category is a proxy for whip status, so the
     biggest outliers should be verified against the historical record
     (some may be formally designated free votes).

Outputs (in results_e1/):
  summary.csv                    per session x party x category dissent table
  whip_test_by_session.png      governing-party whipped vs free dissent rates
  dissent_by_category_pooled.png all parties, all sessions pooled

Usage: python3 experiment_e1.py
"""

import csv
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import bill_info
from visualize_parliament import (PARTY_COLORS, WHIPPED_PARTIES,
                                  find_rebels, load_parliament, vote_number)

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(PROJECT_ROOT, "results_e1")

# Governing party per session. 45-1: Liberal (Carney).
SESSION_GOVERNMENT = {
    "38-1": "Liberal",
    "39-1": "Conservative", "39-2": "Conservative",
    "40-1": "Conservative", "40-2": "Conservative", "40-3": "Conservative",
    "41-1": "Conservative", "41-2": "Conservative",
    "42-1": "Liberal",
    "43-1": "Liberal", "43-2": "Liberal",
    "44-1": "Liberal",
    "45-1": "Liberal",
}

# Sessions excluded from per-session statistics (see README).
EXCLUDED_SESSIONS = {"40-1"}

# A division is "near-unanimous" if more than this share of all votes cast
# in the House fell on one side.
UNANIMITY_THRESHOLD = 0.95

FREE_CATEGORY = "private_members_business"
WHIPPED_CATEGORY = "government_bill"


def is_near_unanimous(meta_row):
    yeas, nays = int(meta_row["yeas"] or 0), int(meta_row["nays"] or 0)
    total = yeas + nays
    return total > 0 and max(yeas, nays) / total > UNANIMITY_THRESHOLD


def gather_session(directory):
    """Count divisions and dissent per (party, category), with and without
    near-unanimous divisions, and collect governing-party rebellions on
    government bills for the outlier list.

    Returns (counts, outliers) where counts[(party, category, variant)] =
    [divisions, with_dissent] for variant in ("all", "contested").
    """
    session = os.path.basename(os.path.normpath(directory)).replace(
        "Parliament_", "")
    government = SESSION_GOVERNMENT.get(session)
    metadata = bill_info.load_vote_metadata(directory)
    bills = load_parliament(directory)

    counts = {}
    outliers = []
    designated_free = []  # (number, rebels, subject) — reported separately

    for bill_name, votes in bills:
        number = vote_number(bill_name)
        if number not in metadata:
            continue
        meta = metadata[number]
        category = meta["category"]
        contested = not is_near_unanimous(meta)
        rebels = find_rebels(votes, WHIPPED_PARTIES)
        gov_rebels = rebels.get(government) if government else None

        # Designated free votes (e.g. C-38 in 38-1) are sanctioned dissent:
        # keep them out of the whipped column entirely and report them.
        if category == WHIPPED_CATEGORY and meta.get("designated_free"):
            designated_free.append((number,
                                    len(gov_rebels) if gov_rebels else 0,
                                    meta["subject"][:70]))
            continue

        for party in WHIPPED_PARTIES:
            party_rebels = rebels[party]
            if party_rebels is None:
                continue
            for variant in ("all",) + (("contested",) if contested else ()):
                cell = counts.setdefault((party, category, variant), [0, 0])
                cell[0] += 1
                if party_rebels:
                    cell[1] += 1

        if (government and category == WHIPPED_CATEGORY
                and gov_rebels):
            outliers.append((session, number, len(gov_rebels),
                             meta["subject"][:90],
                             meta.get("confidence", False)))

    return session, government, counts, outliers, designated_free


def rate(cell):
    """Dissent rate from a [divisions, with_dissent] cell, or None."""
    if not cell or not cell[0]:
        return None
    return round(cell[1] / cell[0] * 100, 2)


def main():
    os.makedirs(RESULTS_DIR, exist_ok=True)

    directories = sorted(
        os.path.join(PROJECT_ROOT, d) for d in os.listdir(PROJECT_ROOT)
        if d.startswith("Parliament_")
        and os.path.isdir(os.path.join(PROJECT_ROOT, d))
        and d.replace("Parliament_", "") not in EXCLUDED_SESSIONS)

    all_rows = []          # for summary.csv
    headline = []          # (session, gov party, whipped rate, free rate) x variant
    pooled = {}            # (party, category, variant) -> [divisions, with_dissent]
    all_outliers = []

    for directory in directories:
        (session, government, counts,
         outliers, designated_free) = gather_session(directory)
        all_outliers.extend(outliers)
        if designated_free:
            with_dissent = sum(1 for _, r, _ in designated_free if r)
            print(f"note: {session}: excluded "
                  f"{len(designated_free)} designated-free government-bill "
                  f"divisions from the whipped column "
                  f"(dissent on {with_dissent}); see "
                  f"bill_info.FREE_VOTE_BILLS.")

        for (party, category, variant), cell in counts.items():
            all_rows.append({
                "session": session, "party": party, "category": category,
                "variant": variant, "divisions": cell[0],
                "with_dissent": cell[1], "dissent_rate": rate(cell)})
            pooled_cell = pooled.setdefault((party, category, variant), [0, 0])
            pooled_cell[0] += cell[0]
            pooled_cell[1] += cell[1]

        if government:
            entry = {"session": session, "government": government}
            for variant in ("all", "contested"):
                entry[f"whipped_{variant}"] = rate(
                    counts.get((government, WHIPPED_CATEGORY, variant)))
                entry[f"free_{variant}"] = rate(
                    counts.get((government, FREE_CATEGORY, variant)))
            headline.append(entry)

    # ---- summary.csv ----------------------------------------------------
    summary_path = os.path.join(RESULTS_DIR, "summary.csv")
    with open(summary_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "session", "party", "category", "variant",
            "divisions", "with_dissent", "dissent_rate"])
        writer.writeheader()
        writer.writerows(sorted(all_rows, key=lambda r: (
            r["session"], r["party"], r["category"], r["variant"])))

    # ---- console report -------------------------------------------------
    print("E1: The whip test — governing party, government bills vs. "
          "private members' business")
    print("=" * 78)
    print(f"{'session':8} {'gov party':13} "
          f"{'whipped%':>9} {'free%':>7}   {'(contested-only variant)':>26}")
    for h in headline:
        contested = (f"whipped {h['whipped_contested']}%, "
                     f"free {h['free_contested']}%")
        print(f"{h['session']:8} {h['government']:13} "
              f"{str(h['whipped_all']):>9} {str(h['free_all']):>7}   "
              f"{contested:>26}")

    print("\nLargest governing-party rebellions on government bills "
          "(spot-check these against the record;")
    print("category is a proxy for whip status and some may be designated "
          "free votes):")
    for session, number, n_rebels, subject, confidence in sorted(
            all_outliers, key=lambda o: -o[2])[:10]:
        conf = " [confidence]" if confidence else ""
        print(f"  {session} vote {number}: {n_rebels} rebels{conf} — {subject}")

    # ---- figure 1: whipped vs free by session ---------------------------
    sessions = [h["session"] for h in headline]
    x = range(len(sessions))
    width = 0.38
    plt.figure(figsize=(14, 7))
    plt.bar([i - width / 2 for i in x],
            [h["whipped_all"] or 0 for h in headline], width,
            label="Government bills (whipped)", color="#444444")
    plt.bar([i + width / 2 for i in x],
            [h["free_all"] or 0 for h in headline], width,
            label="Private members' business (free)", color="#BBBBBB")
    for i, h in enumerate(headline):
        color = PARTY_COLORS[h["government"]]
        plt.plot([i - width, i + width], [-2.5, -2.5], color=color, lw=6,
                 solid_capstyle="butt", clip_on=False)
    plt.xticks(list(x), sessions)
    plt.ylabel("Divisions with any governing-party dissent (%)")
    plt.title("The Whip Test: governing-party dissent, whipped vs. free "
              "business\n(coloured underline = governing party)")
    plt.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(RESULTS_DIR, "whip_test_by_session.png"))
    plt.close()

    # ---- figure 2: pooled dissent by category, all parties --------------
    categories = sorted({c for (_, c, v) in pooled if v == "all"})
    parties = [p for p in WHIPPED_PARTIES
               if any((p, c, "all") in pooled for c in categories)]
    plt.figure(figsize=(15, 7))
    bar_width = 0.8 / max(len(parties), 1)
    for i, party in enumerate(parties):
        xs = [j + i * bar_width for j in range(len(categories))]
        ys = [rate(pooled.get((party, c, "all"))) or 0 for c in categories]
        plt.bar(xs, ys, width=bar_width, label=party,
                color=PARTY_COLORS[party])
    plt.xticks([j + bar_width * (len(parties) - 1) / 2
                for j in range(len(categories))],
               [c.replace("_", "\n") for c in categories])
    plt.ylabel("Divisions with any dissent (%)")
    plt.title("Dissent rate by vote category, all sessions pooled "
              "(2004–present)")
    plt.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(RESULTS_DIR, "dissent_by_category_pooled.png"))
    plt.close()

    print(f"\nWrote {summary_path} and two figures to {RESULTS_DIR}/")


if __name__ == "__main__":
    main()
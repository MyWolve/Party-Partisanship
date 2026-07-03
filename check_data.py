"""Data integrity checks for the scraped vote corpus.

Run after a scrape (especially the backfill of old sessions) and before any
analysis. For every Parliament_<session> directory this verifies:

  1. Coverage      every vote in votes_metadata.csv has a file_<N>.csv,
                   and every file_<N>.csv has a metadata row
  2. Tallies       the Yea/Nay counts summed from each member file match
                   the yeas/nays columns in the metadata (this validates
                   every division against an independent source); paired
                   counts are compared as a soft warning only, since the
                   two sources may count pairs differently
  3. File sanity   vote files parse, have a header, and contain rows
  4. Classifier    subjects falling in the "other" category are listed,
                   since phrasing conventions drift across two decades and
                   older sessions may need new patterns in bill_info.py

Exits nonzero if any hard problem is found, so it can gate a pipeline:

    python3 check_data.py               # check all sessions
    python3 check_data.py 44-1 45-1     # check specific sessions
"""

import csv
import os
import re
import sys

import bill_info

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))


def session_directories(sessions=None):
    """Yield (session, directory) pairs, optionally filtered."""
    for name in sorted(os.listdir(PROJECT_ROOT)):
        path = os.path.join(PROJECT_ROOT, name)
        if not (name.startswith("Parliament_") and os.path.isdir(path)):
            continue
        session = name.replace("Parliament_", "")
        if sessions and session not in sessions:
            continue
        yield session, path


def tally_vote_file(file_path):
    """Return (yeas, nays, paired, data_rows) from one member vote file.

    Returns None if the file is unreadable or has no data rows.
    """
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            reader = csv.reader(f)
            next(reader, None)  # header
            rows = [row for row in reader if len(row) >= 3]
    except (OSError, csv.Error):
        return None
    if not rows:
        return None

    yeas = sum(1 for row in rows if row[2] == "Yea")
    nays = sum(1 for row in rows if row[2] == "Nay")
    paired = sum(1 for row in rows
                 if len(row) >= 4 and row[3].strip() == "Paired")
    return yeas, nays, paired, len(rows)


def check_session(session, directory):
    """Run all checks on one session. Returns (problems, warnings) lists."""
    problems, warnings = [], []

    # --- Load both sides of the join ------------------------------------
    metadata = bill_info.load_vote_metadata(directory)
    vote_files = {
        int(match.group(1)): os.path.join(directory, filename)
        for filename in os.listdir(directory)
        if (match := re.fullmatch(r"file_(\d+)\.csv", filename))
    }

    if not metadata:
        problems.append("no votes_metadata.csv (rerun the scraper's "
                        "metadata step)")
    if not vote_files:
        problems.append("no file_<N>.csv vote files")
    if not metadata or not vote_files:
        return problems, warnings

    # --- 1. Coverage -----------------------------------------------------
    missing = sorted(set(metadata) - set(vote_files))
    orphans = sorted(set(vote_files) - set(metadata))
    if missing:
        problems.append(f"{len(missing)} divisions in metadata with no vote "
                        f"file: {_abbreviate(missing)}")
    if orphans:
        problems.append(f"{len(orphans)} vote files with no metadata row: "
                        f"{_abbreviate(orphans)}")

    # --- 2 & 3. Tallies and file sanity ----------------------------------
    tally_mismatches = []
    paired_mismatches = []
    bad_files = []
    for number in sorted(set(metadata) & set(vote_files)):
        tallied = tally_vote_file(vote_files[number])
        if tallied is None:
            bad_files.append(number)
            continue
        yeas, nays, paired, _ = tallied
        meta = metadata[number]
        expected = (_to_int(meta.get("yeas")), _to_int(meta.get("nays")))
        if (yeas, nays) != expected:
            tally_mismatches.append(
                f"vote {number}: file has {yeas}Y/{nays}N, "
                f"metadata says {expected[0]}Y/{expected[1]}N")
        expected_paired = _to_int(meta.get("paired"))
        if expected_paired is not None and paired != expected_paired:
            paired_mismatches.append(
                f"vote {number}: file has {paired} paired, "
                f"metadata says {expected_paired}")

    if bad_files:
        problems.append(f"{len(bad_files)} unreadable/empty vote files: "
                        f"{_abbreviate(bad_files)}")
    if tally_mismatches:
        problems.append(f"{len(tally_mismatches)} Yea/Nay tally mismatches:")
        problems.extend("  " + line for line in tally_mismatches[:10])
        if len(tally_mismatches) > 10:
            problems.append(f"  ... and {len(tally_mismatches) - 10} more")
    if paired_mismatches:
        warnings.append(f"{len(paired_mismatches)} paired-count differences "
                        f"(may just be counting convention): "
                        f"{_abbreviate([m.split(':')[0] for m in paired_mismatches])}")

    # --- 4. Classifier audit ----------------------------------------------
    others = [(n, m["subject"]) for n, m in sorted(metadata.items())
              if m["category"] == "other"]
    if others:
        warnings.append(f"{len(others)} divisions classified as 'other' "
                        f"(check for patterns to add to bill_info.py):")
        warnings.extend(f"  vote {n}: {subject[:80]}" for n, subject in others[:15])
        if len(others) > 15:
            warnings.append(f"  ... and {len(others) - 15} more")

    return problems, warnings


def _to_int(value):
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def _abbreviate(items, limit=8):
    shown = ", ".join(str(item) for item in items[:limit])
    return shown + (f", ... ({len(items)} total)" if len(items) > limit else "")


def main(sessions=None):
    any_problems = False
    checked = 0

    for session, directory in session_directories(sessions):
        checked += 1
        problems, warnings = check_session(session, directory)
        status = "FAIL" if problems else ("WARN" if warnings else "OK")
        print(f"\n[{status}] Parliament {session}")
        for line in problems:
            print(f"  PROBLEM: {line}")
        for line in warnings:
            print(f"  warning: {line}")
        if problems:
            any_problems = True

    if not checked:
        print("No matching Parliament_* directories found.")
        return 1
    print(f"\n{checked} session(s) checked; "
          + ("problems found." if any_problems else "no hard problems."))
    return 1 if any_problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:] or None))
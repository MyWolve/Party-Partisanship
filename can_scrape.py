"""
Scrape recorded division (vote) data from the House of Commons website.

  Session vote list (XML):
      https://www.ourcommons.ca/members/en/votes/xml?parlSession=44-1
  Per-vote member votes (CSV):
      https://www.ourcommons.ca/members/en/votes/44/1/456/csv

For each session this produces:
  Parliament_<session>/votes_metadata.csv   one row per division: number,
                                            date, subject, bill number,
                                            result, yea/nay/paired counts
  Parliament_<session>/file_<N>.csv         per-member votes for division N
                                            (same format as before)
"""

import csv
import os
import time
import xml.etree.ElementTree as ET

import requests

# Project root = the directory this script lives in.
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

BASE_URL = "https://www.ourcommons.ca"

# Sessions available through the votes interface (verified July 2026).
KNOWN_SESSIONS = [
    "38-1",
    "39-1", "39-2",
    "40-1", "40-2", "40-3",
    "41-1", "41-2",
    "42-1",
    "43-1", "43-2",
    "44-1",
    "45-1",
]

# Some government sites reject the default python-requests user agent,
# which can make valid sessions look like they don't exist.
HEADERS = {
    "User-Agent": ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"),
    "Accept-Language": "en-CA,en;q=0.9",
}

REQUEST_DELAY_SECONDS = 0.5

# Fields to keep from each vote element, in output column order. Tag names
# are matched case-insensitively and by substring, since the export schema
# may differ slightly between deployments; run scrape_session() once and
# check votes_metadata.csv to confirm the columns populated correctly.
METADATA_FIELDS = [
    ("vote_number", ("decisiondivisionnumber",)),
    ("date", ("decisioneventdatetime", "decisiondivisiondatetime")),
    ("subject", ("decisiondivisionsubject",)),
    ("bill_number", ("billnumbercode",)),
    ("result", ("decisionresultname",)),
    ("yeas", ("decisiondivisionnumberofyeas",)),
    ("nays", ("decisiondivisionnumberofnays",)),
    ("paired", ("decisiondivisionnumberofpaired",)),
]


def fetch(url, **kwargs):
    """GET with polite delay, shared headers, and status check."""
    time.sleep(REQUEST_DELAY_SECONDS)
    response = requests.get(url, headers=HEADERS, timeout=30, **kwargs)
    response.raise_for_status()
    return response


def extract_field(element, tag_fragments):
    """Find the first child whose tag contains any fragment (case-insensitive)."""
    for child in element.iter():
        tag = child.tag.lower().rsplit("}", 1)[-1]  # strip any XML namespace
        if any(fragment in tag for fragment in tag_fragments):
            return (child.text or "").strip()
    return ""


def get_session_metadata(session):
    """
    Download and parse the session's vote list from the XML export.

    Returns a list of dicts with the METADATA_FIELDS keys, or None if the
    session isn't served (empty export).
    """
    url = f"{BASE_URL}/members/en/votes/xml?parlSession={session}"
    response = fetch(url)

    root = ET.fromstring(response.content)
    # Vote entries are the repeated child elements of the root; the exact
    # tag name may vary, so take all direct children uniformly.
    entries = list(root)
    if not entries:
        return None

    votes = []
    for entry in entries:
        votes.append({
            name: extract_field(entry, fragments)
            for name, fragments in METADATA_FIELDS
        })
    return votes


def write_metadata_csv(votes, output_dir):
    """Write the session vote metadata to votes_metadata.csv."""
    path = os.path.join(output_dir, "votes_metadata.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[name for name, _ in METADATA_FIELDS])
        writer.writeheader()
        writer.writerows(votes)
    return path


def download_member_votes(session, vote_number, output_dir):
    """
    Download the per-member vote CSV for one division.

    Uses the direct CSV endpoint on the vote detail page, so no HTML
    scraping is needed. Skips the download if the file already exists.
    Returns True if a file was downloaded, False if skipped or failed.
    """
    file_path = os.path.join(output_dir, f"file_{vote_number}.csv")
    if os.path.exists(file_path):
        return False

    parliament, session_number = session.split("-")
    url = f"{BASE_URL}/members/en/votes/{parliament}/{session_number}/{vote_number}/csv"

    try:
        response = fetch(url)
    except requests.RequestException as error:
        print(f"    vote {vote_number}: download failed ({error})")
        return False

    with open(file_path, "wb") as f:
        f.write(response.content)
    return True


def scrape_session(session):
    """Scrape metadata and all per-member vote files for one session."""
    try:
        votes = get_session_metadata(session)
    except (requests.RequestException, ET.ParseError) as error:
        print(f"Session {session}: metadata fetch failed ({error}), skipping.")
        return

    if not votes:
        print(f"Session {session}: no votes returned, skipping.")
        return

    output_dir = os.path.join(PROJECT_ROOT, f"Parliament_{session}")
    os.makedirs(output_dir, exist_ok=True)

    metadata_path = write_metadata_csv(votes, output_dir)
    print(f"Session {session}: {len(votes)} votes; metadata -> {metadata_path}")

    downloaded = 0
    for vote in votes:
        number = vote["vote_number"]
        if number and download_member_votes(session, number, output_dir):
            downloaded += 1
    print(f"Session {session}: downloaded {downloaded} new vote files "
          f"({len(votes) - downloaded} already present or failed).")


def scrape_all(sessions=None):
    for session in sessions or KNOWN_SESSIONS:
        scrape_session(session)


if __name__ == "__main__":
    #scrape_all()
    scrape_session("45-1")
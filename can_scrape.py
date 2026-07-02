"""
Scrape recorded division (vote) data from the House of Commons website.

For each parliamentary session, this script:
  1. Fetches the list of recorded votes and saves their URLs to a CSV.
  2. Visits each vote page and downloads the per-member vote CSV
     into a Parliament_<session>/ directory.

All paths are relative to this file's location, so the script runs
from any machine or working directory.
"""

import csv
import os

import requests
from bs4 import BeautifulSoup

# Project root = the directory this script lives in.
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

BASE_URL = "https://www.ourcommons.ca"
VOTE_LIST_URL = BASE_URL + "/members/en/votes?parlSession="


def get_vote_pages(session, output_csv):
    """
    Fetch the list of vote-detail URLs for a session and write them to output_csv.

    Returns the number of vote URLs found, or None if the session doesn't exist
    (the site returns a 500 for unknown sessions).
    """
    response = requests.get(VOTE_LIST_URL + session)

    if response.status_code != 200:
        return None

    soup = BeautifulSoup(response.text, "html.parser")
    tbody = soup.find("tbody")
    if tbody is None:
        return None

    count = 0
    with open(output_csv, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        for tr in tbody.find_all("tr"):
            td = tr.find("td")
            if td:
                a_tag = td.find("a")
                if a_tag and "href" in a_tag.attrs:
                    writer.writerow([BASE_URL + a_tag["href"]])
                    count += 1
    return count


def get_vote_by_party(vote_pages_csv, output_dir):
    """Download the per-member vote CSV for every vote URL listed in vote_pages_csv."""
    os.makedirs(output_dir, exist_ok=True)

    with open(vote_pages_csv, mode="r", encoding="utf-8") as file:
        for row in csv.reader(file):
            vote_url = row[0]

            response = requests.get(vote_url)
            if response.status_code != 200:
                continue

            soup = BeautifulSoup(response.text, "html.parser")
            div = soup.find("div", class_="pt-2")
            if div is None:
                continue

            a_tags = div.find_all("a")
            if len(a_tags) < 2:
                continue

            href = a_tags[1].get("href")
            file_response = requests.get(BASE_URL + href)
            if file_response.status_code != 200:
                continue

            # The vote number is the last path segment of the URL,
            # e.g. .../votes/41/2/467 -> 467
            vote_number = vote_url.rstrip("/").rsplit("/", 1)[-1]
            file_path = os.path.join(output_dir, f"file_{vote_number}.csv")
            with open(file_path, "wb") as f:
                f.write(file_response.content)


def scrape_sessions(parliaments, sessions_per_parliament=range(1, 4)):
    """Scrape all vote data for the given parliaments (e.g. range(38, 45))."""
    vote_pages_csv = os.path.join(PROJECT_ROOT, "output.csv")

    for parliament in parliaments:
        for session_number in sessions_per_parliament:
            session = f"{parliament}-{session_number}"
            found = get_vote_pages(session, vote_pages_csv)
            if found:
                print(f"Session {session}: {found} votes found, downloading...")
                output_dir = os.path.join(PROJECT_ROOT, f"Parliament_{session}")
                get_vote_by_party(vote_pages_csv, output_dir)
            else:
                print(f"Session {session}: not found, skipping.")


if __name__ == "__main__":
    scrape_sessions(range(38, 42))
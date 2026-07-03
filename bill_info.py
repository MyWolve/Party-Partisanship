"""Bill metadata and vote classification.

Connects the three data sources of this project:

  Parliament_<session>/file_<N>.csv        who voted how (per division)
  Parliament_<session>/votes_metadata.csv  what each division was about
  House of Commons/<session>.xml           LEGISinfo bill details

and classifies each division by the kind of business being voted on, so
dissent can be analyzed separately for whipped and free votes.

Classification produces three fields per division:

  category    government_bill | private_members_business | opposition_motion |
              government_motion | procedural | throne_speech | supply |
              committee_report | other
  stage       second_reading | third_reading | report_stage |
              senate_amendments | amendment | None
  confidence  True for confidence-adjacent business (budget, supply,
              throne speech), which is always whipped for the government

Bill types come from the LEGISinfo XML when available ("House Government
Bill", "Private Member's Bill", etc.); otherwise they are inferred from the
bill number using the House's numbering conventions (C-1 to C-200 government
bills, C-201+ private members' bills, and correspondingly for S- numbers).
"""

import csv
import os
import re
import xml.etree.ElementTree as ET

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
BILL_XML_DIR = os.path.join(PROJECT_ROOT, "House of Commons")


# ---------------------------------------------------------------------------
# Bill types
# ---------------------------------------------------------------------------

def load_bill_types(session):
    """Parse the LEGISinfo XML for a session.

    Returns {bill_number: {"type", "sponsor", "title"}} keyed on the
    formatted number (e.g. "C-30"), or {} if no XML exists for the session.
    """
    path = os.path.join(BILL_XML_DIR, f"{session}.xml")
    if not os.path.exists(path):
        return {}

    bills = {}
    for bill in ET.parse(path).getroot().findall("Bill"):
        number = (bill.findtext("BillNumberFormatted") or "").strip()
        if number:
            bills[number] = {
                "type": (bill.findtext("BillTypeEn") or "").strip(),
                "sponsor": (bill.findtext("SponsorEn") or "").strip(),
                "title": (bill.findtext("LongTitleEn") or "").strip(),
            }
    return bills


def infer_bill_type(bill_number):
    """Infer a bill's type from House numbering conventions.

    Used as a fallback when no LEGISinfo XML is available for the session.
    """
    match = re.fullmatch(r"([CS])-(\d+)", bill_number.strip())
    if not match:
        return ""
    chamber, number = match.group(1), int(match.group(2))
    if chamber == "C":
        return ("House Government Bill" if number <= 200
                else "Private Member's Bill")
    if number <= 200:
        return "Senate Government Bill"
    if number <= 1000:
        return "Senate Public Bill"
    return "Senate Private Bill"


def bill_type_for(bill_number, bill_types):
    """Look up a bill's type in the XML data, falling back to inference."""
    if not bill_number:
        return ""
    info = bill_types.get(bill_number)
    if info and info["type"]:
        return info["type"]
    return infer_bill_type(bill_number)


# ---------------------------------------------------------------------------
# Vote classification
# ---------------------------------------------------------------------------

# Ordered pattern tables: the first match wins, so procedural motions about
# a bill (e.g. time allocation) classify as procedural, not as bill votes.
_CATEGORY_PATTERNS = [
    ("procedural", re.compile(
        # "tme allocation" is a typo in the official record (42-1 vote 997)
        r"time allocation|tme allocation|closure|be not further adjourned"
        r"|motion to proceed to|extension of sitting hours"
        r"|motion to adjourn|previous question|motion to hear another member"
        r"|production of papers|question of privilege"
        r"|proceedings and business of the house", re.I)),
    ("opposition_motion", re.compile(r"opposition motion", re.I)),
    ("government_motion", re.compile(
        r"government business no|declaration of emergency", re.I)),
    ("private_members_business", re.compile(
        r"^private members' business", re.I)),
    ("throne_speech", re.compile(r"address in reply", re.I)),
    ("supply", re.compile(
        r"^budgetary policy|estimates|interim supply|ways and means"
        r"|opposed item|granting to (his|her) majesty certain sums", re.I)),
    ("appointment", re.compile(r"appointment of an officer of parliament",
                               re.I)),
    ("committee_report", re.compile(
        # Some older subjects contain leaked template text before
        # "Report of the ..." (41-2 vote 373), so match loosely.
        r"report of the|concurrence in the .* report", re.I)),
]

_STAGE_PATTERNS = [
    ("second_reading", re.compile(r"2nd reading", re.I)),
    ("third_reading", re.compile(r"3rd reading", re.I)),
    ("report_stage", re.compile(r"report stage|concurrence at report", re.I)),
    ("senate_amendments", re.compile(r"senate amendment", re.I)),
]

_CONFIDENCE_PATTERN = re.compile(
    r"budget|economic update|fiscal update|interim supply|estimates"
    r"|granting to (his|her) majesty certain sums|address in reply"
    r"|confidence in the government|ways and means"
    r"|declaration of emergency", re.I)

_BILL_IN_SUBJECT = re.compile(r"\bBill ([CS]-\d+)")


def classify_vote(subject, bill_number, bill_types):
    """Classify one division.

    Returns {"category", "stage", "confidence", "bill_number", "bill_type"}.
    The bill number is recovered from the subject text when the metadata
    column is empty (e.g. Government Business motions about a bill).
    """
    if not bill_number:
        match = _BILL_IN_SUBJECT.search(subject)
        bill_number = match.group(1) if match else ""

    bill_type = bill_type_for(bill_number, bill_types)

    category = None
    for name, pattern in _CATEGORY_PATTERNS:
        if pattern.search(subject):
            category = name
            break

    if category is None and bill_number:
        if "Government Bill" in bill_type:
            category = "government_bill"
        elif bill_type in ("Private Member's Bill", "Senate Public Bill"):
            category = "private_members_business"
        else:
            category = "government_bill"  # unknown bill type: safer default
    elif category is None and re.match(r"bill\b", subject, re.I):
        # Malformed source subjects like "Bill ,  (report stage subamendment)"
        # (42-1 vote 247) name a bill but lost its number; treat as a bill
        # vote of unknown type.
        category = "government_bill"
    elif category is None:
        category = "other"

    stage = None
    for name, pattern in _STAGE_PATTERNS:
        if pattern.search(subject):
            stage = name
            break
    if stage is None and re.search(r"\(amendment\)|\(subamendment\)", subject, re.I):
        stage = "amendment"

    return {
        "category": category,
        "stage": stage,
        "confidence": bool(_CONFIDENCE_PATTERN.search(subject)),
        "bill_number": bill_number,
        "bill_type": bill_type,
    }


# Categories where MPs traditionally vote freely (no whip, or a loose one).
FREE_VOTE_CATEGORIES = {"private_members_business"}


# ---------------------------------------------------------------------------
# Metadata loading and joining
# ---------------------------------------------------------------------------

def load_vote_metadata(directory):
    """Load and classify a session's votes_metadata.csv.

    Returns {vote_number (int): metadata dict} with classification fields
    merged in, or {} if the session has no metadata file (in which case
    category-based analyses are unavailable but everything else still works).
    """
    path = os.path.join(directory, "votes_metadata.csv")
    if not os.path.exists(path):
        return {}

    session = os.path.basename(os.path.normpath(directory)).replace(
        "Parliament_", "")
    bill_types = load_bill_types(session)

    metadata = {}
    with open(path, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            if not row.get("vote_number", "").strip():
                continue
            number = int(row["vote_number"])
            row.update(classify_vote(row.get("subject", ""),
                                     row.get("bill_number", "").strip(),
                                     bill_types))
            metadata[number] = row
    return metadata
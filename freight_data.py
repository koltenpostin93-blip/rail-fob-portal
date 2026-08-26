"""
Static rail freight reference data — CSX + NS + BN origin spread tables.

Seeded from Kolten's "Rail Spreads.xlsx"
(`…\\Research Analyst\\Misc\\Rail Origins & Destinations\\`), CSX/NS/BN tabs,
via one-off extractions (CSX+NS: 2026-08-21; BN: 2026-08-25).
`csx_freight_seed.json` / `ns_freight_seed.json` / `bn_freight_seed.json` are
committed snapshots — re-run the extraction and overwrite them if Kolten
sends an updated workbook; this module doesn't touch the source file at
runtime.

CSX/NS rows' `highlighted` flag comes straight from an "X"/"x" marker column
Kolten added to the workbook itself — not a hardcoded shortlist. BN's sheet
has no such marker (only 11 origins total, no separate curated subset).

CSX rates are $/car at the workbook's stated 3500 bu/car. NS rates are
already $/bu. BN rates are $/car at 4000 bu/car (confirmed by cross-checking
its own $/bu sub-table: $/car ÷ 4000 reproduces it exactly). All convert to
¢/bu for display, matching the bid side's units.
"""
import json
import os
import re

_DIR = os.path.dirname(__file__)

CSX_BU_PER_CAR = 3500

# CSX bid-market -> freight column(s) that net against it. Evansville has two
# published variants (by downstream market); AL/TN/KY/LA is the primary one,
# GA/FL is flagged when it differs (Kolten's call, 2026-08-21).
CSX_CORRIDORS = {
    "CSX Columbus":   {"field": "columbus", "market": "CSX Columbus"},
    "CSX Evansville": {"field": "eville_altkyla", "alt_field": "eville_gafl",
                        "market": "CSX Evansville"},
}

# NS has one bid market (Ft Wayne) with three published rate variants by
# downstream market — same "through rate" pattern as CSX's dual Evansville
# rate, just three-wide instead of two (Kolten confirmed, 2026-08-21).
NS_REGIONS = {
    "GA":        "ga",
    "NC/SC/VA":  "ncscva",
    "East":      "east",
}
NS_BID_MARKET = "NS Ft Wayne"

# BN publishes rates by delivery month rather than one flat number — a
# genuinely different shape from CSX/NS. The "Tarif + FSC + Cars" table is
# just a ROLLING ~4-month-ahead window (Kolten, 2026-08-25: "all it is is
# shows the 4 most nearby months") — its header months (and presumably the
# underlying numbers) change whenever Kolten updates the workbook, so
# `load_bn()` always reflects whatever's currently published rather than a
# fixed set. Months outside that window have no published rate at all.
#
# A period nets against the freight for its FIRST named month (Kolten's
# call): "Sep 25-Oct 5" -> Sep, "OCT-MAR" -> Oct, "LH OND" -> Oct (OND is a
# package meaning Oct/Nov/Dec), "JFM" -> Jan (a package meaning Jan/Feb/Mar)
# -> blank if Jan isn't in the current window. "IN TRANSIT"/"RETURN TRIP"
# name no month at all -> blank. This mirrors rail_corridors.py's
# package/month parsing conventions used elsewhere for CSX, but BN's own
# period labels (LH OND, SEP 25-OCT 5, RETURN TRIP...) needed slightly more
# tolerant parsing (a stripped qualifier prefix, packages matched mid-string)
# so it's kept separate rather than importing that module's stricter version.
BN_BU_PER_CAR = 4000
BN_DESTINATIONS = {
    "PNW":      {"field": "pnw", "market": "BN PNW"},
    "Hereford": {"field": "hereford", "market": "BN Hereford"},
}

_BN_MONTH3 = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
              "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12}
_BN_MONTH3_REV = {v: k for k, v in _BN_MONTH3.items()}
_BN_PACKAGES = {"jfm": 1, "fma": 2, "mam": 3, "amj": 4, "mjj": 5, "jja": 6,
                 "jas": 7, "aso": 8, "son": 9, "ond": 10, "ndj": 11, "djf": 12,
                 "amjj": 4, "am": 4, "jj": 6, "as": 8}


def bn_period_first_month(period):
    """First named calendar month (1-12) in a period label, or None if it
    names no month at all (e.g. "In Transit", "Return Trip")."""
    p = re.sub(r"^\s*(FH|LH|MP|SPLIT|FULL)\b\s*", "", period.strip(), flags=re.I).lower()
    if p in _BN_PACKAGES:
        return _BN_PACKAGES[p]
    found = [(p.find(tok), m) for tok, m in _BN_MONTH3.items() if tok in p]
    if not found:
        return None
    found.sort()
    return found[0][1]


def bn_month_sort_key(month_key):
    """Calendar order for a seed-data month key (e.g. 'oct' -> 10), so
    callers can list an origin's published months in the right order
    regardless of which months are currently in the rolling window."""
    return _BN_MONTH3.get(month_key, 99)


def bn_freight_cpb(month_rates, period):
    """month_rates: whatever months are CURRENTLY published, e.g.
    {'aug':..,'sep':..,'oct':..,'nov':..} in ¢/bu (already converted) — the
    exact set rolls over time. Returns the rate for `period`'s first named
    month if that month is in the current window, else None. A legacy 'jj'
    key (if ever present again) covers both Jun and Jul."""
    m = bn_period_first_month(period)
    if m is None:
        return None
    key = _BN_MONTH3_REV[m]
    if key in month_rates:
        return month_rates[key]
    if m in (6, 7) and "jj" in month_rates:
        return month_rates["jj"]
    return None


def _load(name):
    with open(os.path.join(_DIR, name), encoding="utf-8") as f:
        return json.load(f)


def load_csx():
    """[{state, origin_group, train_type, buying_station, highlighted,
         columbus, eville_gafl, eville_altkyla,      <- $/car
         columbus_cpb, eville_gafl_cpb, eville_altkyla_cpb}]  <- ¢/bu"""
    rows = _load("csx_freight_seed.json")
    for r in rows:
        for f in ("columbus", "eville_gafl", "eville_altkyla"):
            r[f"{f}_cpb"] = r[f] / CSX_BU_PER_CAR * 100
    return rows


def load_ns():
    """[{origin, state, highlighted, flag_105,
         ga, ncscva, east,               <- $/bu
         ga_cpb, ncscva_cpb, east_cpb}]  <- ¢/bu"""
    rows = _load("ns_freight_seed.json")
    for r in rows:
        for f in ("ga", "ncscva", "east"):
            r[f"{f}_cpb"] = r[f] * 100
    return rows


def load_bn():
    """[{origin, state,
         pnw: {<current ~4 months>: $/car},
         hereford: {<current ~4 months>: $/car},
         pnw_cpb: {...same keys...: ¢/bu},
         hereford_cpb: {...same keys...: ¢/bu}}]
    The month keys are whatever's currently published — re-run the
    extraction against a freshly saved workbook to roll them forward."""
    rows = _load("bn_freight_seed.json")
    for r in rows:
        for f in ("pnw", "hereford"):
            r[f"{f}_cpb"] = {m: v / BN_BU_PER_CAR * 100 for m, v in r[f].items()}
    return rows


# CN's sheet is a straight copy of its published Gulf Export tariff (CN
# 004050-A8), not a hand-built spread table like the others. All 187 rows go
# to one destination ("Gulf Exports Group"); rate_a-d are the tariff's own
# rate-column definitions (car size × railway- vs shipper-supplied
# equipment), and multiple rows per origin are different volume/condition
# tiers keyed by `notes` (see CN_NOTES below) — e.g. note "4" = 105+ car
# blocks, matching the existing "CN 105s" bid market; note "1" = 25-49 cars,
# matching "CN 25's". Kolten (2026-08-26): upload the raw rates only for
# now — no bu/car figure or FOB netback logic yet; he's still sorting out
# the basis side, which will reference Corn CIF NOLA from the River FOB
# Portal rather than a rail_fob bid market like CSX/NS/BN use.
CN_NOTES = {
    "1": "Car blocks of 25 to 49 cars",
    "2": "Excludes reciprocal switch at origin",
    "3": "Car blocks of 50 to 104 cars",
    "4": "Car blocks of 105 cars or greater",
    "5": "Not subject to AAR Rule 11 billing at origin",
    "6": "USD, collect (invoiced by destination carrier)",
    "7": "Subject to AAR Rule 11 billing at origin",
    "8": "Includes reciprocal switch at origin, up to $139/car",
    "9": "Car blocks of 50 to 84 cars",
    "10": "Car blocks of 85 cars or more",
}
# Kolten's relabeling (2026-08-26): the tariff's own "A/B/C/D" + cubic-foot/
# supplied-by jargon becomes two independent filterable dimensions —
# car SIZE (Small ≤5149 ft³ vs Large >5149 ft³) and car SOURCE (Railroad-
# supplied vs Private/shipper-supplied) — since that's what a shipper
# actually chooses between, not the tariff's letter codes.
CN_SIZES = {"Small": "≤5149 ft³", "Large": ">5149 ft³"}
CN_SOURCES = {"Railroad": "railway-supplied equipment", "Private": "shipper-supplied equipment"}
CN_RATE_FIELD = {
    ("Small", "Railroad"): "rate_a",
    ("Large", "Railroad"): "rate_b",
    ("Small", "Private"):  "rate_c",
    ("Large", "Private"):  "rate_d",
}


def load_cn():
    """[{origin, state, destination, rate_a, rate_b, rate_c, rate_d, notes,
         rate_a_cpb, rate_b_cpb, rate_c_cpb, rate_d_cpb}]
    a/c fields are $/car and ¢/bu for Small cars, b/d for Large — see
    CN_BU_PER_CAR below for the bushel figures behind the conversion."""
    rows = _load("cn_freight_seed.json")
    for r in rows:
        for (size, _source), field in CN_RATE_FIELD.items():
            r[f"{field}_cpb"] = r[field] / CN_BU_PER_CAR[size] * 100
    return rows


# Bushels/car for CN's two size classes, confirmed with Kolten (2026-08-26):
# weight-based hopper-car capacity (Soy Transportation Coalition — 100-ton/
# 4750 ft³ and 110-ton/5750 ft³ reference cars, net payload ÷ corn's 56 lb/bu)
# rather than a naive volumetric conversion, since grain shipments are
# weight-limited, not volume-limited. Depends only on car SIZE — a
# railroad-supplied vs private car of the same size class holds the same
# number of bushels, the ownership doesn't change the car's capacity.
CN_BU_PER_CAR = {"Small": 3570, "Large": 3930}

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

# BN publishes rates by delivery month (Mar/Apr/May/JJ) rather than one flat
# number — a genuinely different shape from CSX/NS. Kolten's call
# (2026-08-25): net each month's rate only against a bid period with the
# EXACT matching label (case-insensitive) — most current postings (Aug, Sep,
# Oct, JFM, OND, etc.) won't match any of these 4 and will show no freight
# for BN until a bid period literally named e.g. "Mar" appears.
BN_BU_PER_CAR = 4000
BN_DESTINATIONS = {
    "PNW":      {"field": "pnw", "market": "BN PNW"},
    "Hereford": {"field": "hereford", "market": "BN Hereford"},
}


def bn_freight_cpb(month_rates, period):
    """month_rates: {'mar':.., 'apr':.., 'may':.., 'jj':..} in ¢/bu (already
    converted). Returns the rate for `period` if its label exactly matches
    (case-insensitive) one of those months, else None."""
    return month_rates.get(period.strip().lower())


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
         pnw: {mar,apr,may,jj},           <- $/car
         hereford: {mar,apr,may,jj},      <- $/car
         pnw_cpb: {mar,apr,may,jj},       <- ¢/bu
         hereford_cpb: {mar,apr,may,jj}}] <- ¢/bu"""
    rows = _load("bn_freight_seed.json")
    for r in rows:
        for f in ("pnw", "hereford"):
            r[f"{f}_cpb"] = {m: v / BN_BU_PER_CAR * 100 for m, v in r[f].items()}
    return rows

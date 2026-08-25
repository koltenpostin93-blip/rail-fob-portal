"""
Rail FOB Sheet — JPSI

Read-only sheet view of the rail corridor bids/offers already archived by the
basis tracker (`rail_fob` table, sources 'manual' + 'palmetto'), plus a
static-freight netback calculator (CSX / NS origin spreads -> FOB) built from
Kolten's Rail Spreads.xlsx. Visual language matches the River FOB Portal
(Source Sans Pro, JPSI dark/blue, card-style "sheet-wrap" tables, background-
tinted up/down cells) per Kolten's 2026-08-24 request to restart the styling
from that reference instead of the original dense mono-terminal look.

Three top-level tabs keep the raw bid boards separate from the CSX/NS origin
economics, instead of one long mixed scroll.
"""
import base64
import os
from collections import Counter

import streamlit as st
import streamlit.components.v1 as components

import freight_data as FD
import rail_data as RD
from rail_corridors import MANUAL_SECTIONS, RAIL_DISPLAY, RAIL_COLORS

# Local .env, optional (Streamlit Cloud uses st.secrets instead).
try:
    from dotenv import load_dotenv
    load_dotenv()
except ModuleNotFoundError:
    pass

try:
    if "BASIS_DATABASE_URL" in st.secrets and not os.environ.get("BASIS_DATABASE_URL"):
        os.environ["BASIS_DATABASE_URL"] = st.secrets["BASIS_DATABASE_URL"]
except Exception:
    pass  # st.secrets unavailable locally — fine, .env covers it

st.set_page_config(
    page_title="Rail Corridors · JPSI",
    page_icon="https://www.jpsi.com/wp-content/uploads/2019/04/cropped-Favicon-1-192x192.png",
    layout="wide",
    initial_sidebar_state="collapsed",
)


@st.cache_data
def _asset_uri(filename):
    p = os.path.join(os.path.dirname(__file__), "assets", filename)
    try:
        with open(p, "rb") as f:
            return "data:image/png;base64," + base64.b64encode(f.read()).decode()
    except OSError:
        return ""


WATERMARK = _asset_uri("jsa_50yr.png")
LOGO_URI = _asset_uri("logo-full.png")

JPSI_DARK = "#32373c"
JPSI_BLUE = "#0693e3"

st.markdown(
    f"""
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Source+Sans+Pro:wght@300;400;600;700&display=swap');
      html, body, [class*="css"], .stApp, button, input, select, textarea, table, td, th,
      .stMarkdown, h1, h2, h3, h4, h5, h6, p, span, div {{
        font-family: 'Source Sans Pro', system-ui, -apple-system, sans-serif !important;
      }}
      table td, table th {{ font-variant-numeric: tabular-nums; }}

      header[data-testid="stHeader"] {{ display: none !important; }}
      #MainMenu {{ visibility: hidden !important; }}
      footer {{ visibility: hidden !important; }}
      .block-container {{ padding-top: 0.75rem !important; padding-bottom: 1rem !important; max-width: 1300px; }}
      .stApp {{ background-color: #ffffff; }}

      .dash-header {{
        background: #ffffff; border-bottom: 3px solid {JPSI_BLUE};
        padding: 18px 8px 14px 8px; margin: -0.75rem 0 22px 0;
        display: flex; align-items: center; gap: 20px;
      }}
      .dash-header-logo {{ flex-shrink: 0; }}
      .dash-header-logo img {{ height: 54px; display: block; }}
      .dash-header-text {{ flex: 1; text-align: center; }}
      .dash-header-text h1 {{
        margin: 0; color: {JPSI_DARK} !important; font-size: 1.7rem;
        font-weight: 700; letter-spacing: -0.01em;
      }}
      .dash-header-text .subtitle {{ color: #6b7280; font-size: 0.85rem; margin: 3px 0 0 0; }}

      h2, h3, h4 {{ color: {JPSI_DARK} !important; font-weight: 700 !important; }}
      h2 {{ border-bottom: 3px solid {JPSI_BLUE}; padding-bottom: 8px;
            margin-top: 24px; margin-bottom: 16px; }}
      h3 {{ margin-top: 20px; margin-bottom: 10px; }}

      .sheet-wrap {{
        border-radius: 10px; overflow: hidden; position: relative;
        box-shadow: 0 2px 8px rgba(50,55,60,0.12); border: 1px solid #ddd;
        background: #fff; margin-bottom: 18px;
      }}
      .sheet-wrap::after {{
        content: ""; position: absolute; inset: 0;
        background: url('{WATERMARK}') center 46% / 32% auto no-repeat;
        opacity: 0.05; pointer-events: none; z-index: 0;
      }}
      .sheet-wrap-inner {{ position: relative; z-index: 1; overflow-x: auto; }}

      table.sheet {{ width: 100%; border-collapse: collapse; font-size: 0.85rem; }}
      table.sheet th {{
        font-size: 0.68rem; font-weight: 700; color: #6b7280; text-transform: uppercase;
        letter-spacing: .03em; padding: 7px 10px; border-bottom: 2px solid #e2e8f0;
        text-align: right; white-space: nowrap;
      }}
      table.sheet th.lblhdr {{ text-align: left; }}
      table.sheet td {{
        padding: 6px 10px; text-align: right; border-bottom: 1px solid #f5f5f5;
        color: #333; white-space: nowrap;
      }}
      table.sheet tr.section td {{
        background: #f0f0f0; color: {JPSI_DARK}; font-weight: 700;
        padding: 7px 16px; border-top: 1px solid #ddd; border-bottom: none;
        font-size: 0.75rem; text-transform: uppercase; letter-spacing: .04em;
        text-align: left;
      }}
      table.sheet tr.origin-hdr td {{
        padding: 10px 10px 4px 10px; border-bottom: none; font-weight: 700;
        color: {JPSI_DARK}; text-align: left;
      }}
      table.sheet td.lbl {{ text-align: left; font-weight: 600; color: #2c3e50; }}
      table.sheet td.sub-lbl {{
        text-align: left; color: #6b7280; padding-left: 26px; font-style: italic;
      }}
      table.sheet td.up {{ background: #e8f5e9; color: #1f2328; font-weight: 700; }}
      table.sheet td.down {{ background: #ffebee; color: #1f2328; font-weight: 700; }}
      table.sheet td.better {{ background: #eaf4fc; color: {JPSI_DARK}; font-weight: 700; }}
      table.sheet td.pending {{ color: #94a3b8; }}
      table.sheet .off {{ color: {JPSI_BLUE}; font-weight: 600; }}
      .fut-sub {{ font-size: 0.68rem; color: #9aa5b1; font-weight: 400; }}
      .rail-chip {{
        font-size: 9px; color: #fff; padding: 2px 7px; border-radius: 8px;
        margin-left: 6px; font-weight: 700;
      }}
      .asof-chip {{
        font-size: 9px; color: #fff; background: #d97706; padding: 2px 7px;
        border-radius: 8px; margin-left: 6px;
      }}
      .legend {{ font-size: 0.78rem; color: #6b7280; padding: 4px 2px 14px 2px; }}
      .legend .sw {{
        display: inline-block; width: 11px; height: 11px; border-radius: 3px;
        vertical-align: middle; margin: 0 4px 0 10px;
      }}
      .legend .sw.up {{ background: #e8f5e9; border: 1px solid #0d7f3d; }}
      .legend .sw.dn {{ background: #ffebee; border: 1px solid #c00000; }}
      .legend .sw.bt {{ background: #eaf4fc; border: 1px solid {JPSI_BLUE}; }}

      .stButton > button {{
        background: {JPSI_BLUE}; color: #fff; border: none; border-radius: 6px; font-weight: 600;
      }}
      .stButton > button:hover {{ background: #057ec2; color: #fff; }}
      label {{ color: {JPSI_DARK} !important; font-weight: 600 !important; }}

      .stTabs [data-baseweb="tab-list"] {{ gap: 0; background: #ffffff; border-bottom: 1px solid #e2e8f0; }}
      [role="tab"], [role="tab"] *, .stTabs [data-baseweb="tab"], .stTabs [data-baseweb="tab"] * {{
        color: {JPSI_DARK} !important; opacity: 1 !important; font-weight: 700 !important;
        font-size: 14px !important; -webkit-text-fill-color: {JPSI_DARK} !important;
      }}
      [role="tab"] {{ padding: 8px 18px; border-radius: 0; }}
      [role="tab"]:hover, [role="tab"]:hover * {{
        color: {JPSI_BLUE} !important; -webkit-text-fill-color: {JPSI_BLUE} !important;
      }}
      [role="tab"][aria-selected="true"] {{ border-bottom: 3px solid {JPSI_BLUE} !important; }}
      [role="tab"][aria-selected="true"], [role="tab"][aria-selected="true"] * {{
        color: #000000 !important; -webkit-text-fill-color: #000000 !important; font-weight: 800 !important;
      }}
      .stTabs [data-baseweb="tab-panel"] {{ padding-top: 10px !important; }}
    </style>
    """,
    unsafe_allow_html=True,
)

_logo_html = (f'<img src="{LOGO_URI}" alt="John Stewart &amp; Associates">' if LOGO_URI else '')
st.markdown(
    f'<div class="dash-header">'
    f'  <div class="dash-header-logo">{_logo_html}</div>'
    f'  <div class="dash-header-text">'
    f'    <h1>Rail Corridors</h1>'
    f'    <div class="subtitle">Commodity &amp; Ag Risk Management Specialists &nbsp;·&nbsp; est. 1976</div>'
    f'  </div>'
    f'  <div style="width:180px"></div>'
    f'</div>',
    unsafe_allow_html=True,
)

if not RD.configured():
    st.warning(
        "BASIS_DATABASE_URL isn't set, so this portal can't reach the basis "
        "tracker's archive yet. Add it to `.env` locally or as a Streamlit "
        "secret to see live data."
    )
    st.stop()


@st.cache_data(ttl=300)
def _cached_dates(source):
    return RD.get_dates(source)


@st.cache_data(ttl=300)
def _cached_all(source):
    return RD.get_all(source)


def _card_open():
    return '<div class="sheet-wrap"><div class="sheet-wrap-inner">'


def _card_close():
    return '</div></div>'


def _disp(num, raw):
    """Prefer the raw display token (?, notations) over the parsed number."""
    if raw:
        return raw
    return f"{num:+d}" if num is not None else None


def _period_key(period_order, period):
    return (period_order if period_order is not None else 99, period)


# Periods to hide from every table on this sheet (still archived as posted —
# this is display-only). "Nov (No Holiday)" duplicates the plain "Nov" column.
_DROP_PERIODS = {"nov (no holiday)"}


def _keep_period(p):
    return p.strip().lower() not in _DROP_PERIODS


def _location_only(buying_station):
    """CSX's buying_station is stored "COMPANY | TOWN" — drop the company,
    keep just the location (Kolten's call, 2026-08-24: company names clutter
    the location labels)."""
    if not buying_station:
        return ""
    return buying_station.split("|", 1)[-1].strip() if "|" in buying_station else buying_station


def _prior_row(mkt_dates_sorted, by_md, market, eff_date):
    """The market's previous posting strictly before eff_date, or None."""
    earlier = [d for d in mkt_dates_sorted.get(market, ()) if d < eff_date]
    return by_md.get((market, earlier[-1])) if earlier else None


def _cell_html(cell, prior_map):
    """One <td> for a corridor × period cell, tinted like a spreadsheet
    change cell (green/red background) rather than colored bold text."""
    if cell is None:
        return '<td>—</td>'
    bid_disp = _disp(cell.get("bid"), cell.get("bid_raw"))
    if bid_disp is None:
        return '<td>—</td>'
    if bid_disp == "?":
        return '<td class="pending">?</td>'
    prior_cell = (prior_map or {}).get(cell["period"])
    pb = prior_cell.get("bid") if prior_cell else None
    b = cell.get("bid")
    cls = ""
    if pb is not None and b is not None and b != pb:
        cls = "up" if b > pb else "down"
    txt = bid_disp
    off_disp = _disp(cell.get("offer"), cell.get("offer_raw"))
    if off_disp:
        txt += f' <span class="off">/ {off_disp}</span>'
    cls_attr = f' class="{cls}"' if cls else ''
    return f'<td{cls_attr}>{txt}</td>'


def _sheet_board(source, sections, key, other_keep=None):
    """other_keep: if given, only these market names may appear in the
    catch-all "Other" section (leftover markets not in any named section);
    pass None to keep every leftover (the old default)."""
    dates = _cached_dates(source)
    if not dates:
        st.caption("No postings archived yet for this board.")
        return None

    sel_col, _ = st.columns([3, 7])
    with sel_col:
        sel_date = st.selectbox("Posting date", dates, key=f"rail_sheet_date_{key}")

    rows = _cached_all(source)
    by_md, mkt_dates = {}, {}
    for r in rows:
        by_md.setdefault((r["market"], r["date"]), {})[r["period"]] = r
        mkt_dates.setdefault(r["market"], set()).add(r["date"])
    mkt_dates_sorted = {m: sorted(ds) for m, ds in mkt_dates.items()}

    placed = {m for _, ms in sections for m in ms}
    elig_markets = {m for m, ds in mkt_dates.items() if any(d <= sel_date for d in ds)}
    leftover = sorted(elig_markets - placed)
    if other_keep is not None:
        leftover = [m for m in leftover if m in other_keep]
    all_sections = list(sections) + ([("Other", leftover)] if leftover else [])

    for title, markets in all_sections:
        section_rows = []
        for m in markets:
            elig = [d for d in mkt_dates_sorted.get(m, ()) if d <= sel_date]
            if not elig:
                continue
            eff = max(elig)
            cells = by_md.get((m, eff), {})
            if not cells:
                continue
            prior = _prior_row(mkt_dates_sorted, by_md, m, eff)
            section_rows.append((m, eff, cells, prior))
        if not section_rows:
            continue

        col_keys = {}
        for _, _, cells, _ in section_rows:
            for p, c in cells.items():
                if _keep_period(p):
                    col_keys.setdefault(p, _period_key(c.get("period_order"), p))
        periods = sorted(col_keys, key=lambda p: col_keys[p])

        col_fut = {}
        for p in periods:
            futs = [cells[p].get("futures") for _, _, cells, _ in section_rows
                    if p in cells and cells[p].get("futures")]
            col_fut[p] = Counter(futs).most_common(1)[0][0] if futs else ""

        ncols = 1 + len(periods)
        html = [_card_open(), '<table class="sheet"><tbody>',
                f'<tr class="section"><td colspan="{ncols}">{title}</td></tr>',
                '<tr>', '<th class="lblhdr">Corridor</th>']
        for p in periods:
            fut = col_fut[p]
            sub = f'<br><span class="fut-sub">{fut}</span>' if fut else ''
            html.append(f'<th>{p}{sub}</th>')
        html.append('</tr>')

        for m, eff, cells, prior in section_rows:
            rail = cells[next(iter(cells))].get("rail") or ""
            rcol = RAIL_COLORS.get(rail, "#64748b")
            asof = ''
            if eff != sel_date:
                yy, mo, dd = eff.split("-")
                asof = f'<span class="asof-chip">as of {int(mo)}/{int(dd)}</span>'
            label = RAIL_DISPLAY.get(m, m)
            html.append(
                f'<tr><td class="lbl">{label}'
                f'<span class="rail-chip" style="background:{rcol}">{rail}</span>'
                f'{asof}</td>'
            )
            for p in periods:
                html.append(_cell_html(cells.get(p), prior))
            html.append('</tr>')
        html.append('</tbody></table>')
        html.append(_card_close())
        st.markdown(''.join(html), unsafe_allow_html=True)

    st.markdown(
        f'<div class="legend">As of {sel_date} · a corridor not posted that day carries '
        'forward its most recent posting (amber "as of M/D") · '
        '<span class="sw up"></span>up <span class="sw dn"></span>down vs that corridor\'s '
        'previous posting · offer shown in blue after "/" · values are archived exactly as '
        'posted, no roll or spread math applied · ? = pending side.</div>',
        unsafe_allow_html=True,
    )
    return sel_date


def _fob_cell(v, better=False):
    if v is None:
        return '<td>—</td>'
    cls = ' class="better"' if better else ''
    return f'<td{cls}>{v:+.1f}</td>'


def _bid_cells_for(source, market, sel_date):
    """Effective (carry-forward) {period: row} for one market at/≤ sel_date,
    plus the actual posting date used (for an 'as of' note)."""
    if sel_date is None:
        return {}, None
    rows = _cached_all(source)
    dates = sorted({r["date"] for r in rows if r["market"] == market and r["date"] <= sel_date})
    if not dates:
        return {}, None
    eff = dates[-1]
    return {r["period"]: r for r in rows if r["market"] == market and r["date"] == eff}, eff


def _period_union(*cell_dicts):
    keys = {}
    for cells in cell_dicts:
        for p, c in cells.items():
            if _keep_period(p):
                keys.setdefault(p, _period_key(c.get("period_order"), p))
    return sorted(keys, key=lambda p: keys[p])


def _fob_cell_int(v, better=False):
    if v is None:
        return '<td>—</td>'
    cls = ' class="better"' if better else ''
    return f'<td{cls}>{round(v):+d}</td>'


def _variant_value_rows(label_rows, cell_fn=_fob_cell, row_label_fn=lambda lbl: f'via {lbl}'):
    """label_rows: [(label, [value_or_None per period]), ...] — one <tr> per
    label. The best (max) value per period across ALL given rows is tinted
    (via `cell_fn`'s `better` flag), so this one function drives both CSX's
    2-way and NS's up-to-3-way comparisons, and the state-level rollups."""
    rows_html = []
    for i, (label, row) in enumerate(label_rows):
        better = []
        for pi in range(len(row)):
            v = row[pi]
            others = [label_rows[j][1][pi] for j in range(len(label_rows)) if j != i and label_rows[j][1][pi] is not None]
            better.append(v is not None and bool(others) and all(v > o for o in others))
        cells_html = ''.join(cell_fn(v, b) for v, b in zip(row, better))
        rows_html.append(f'<tr><td class="sub-lbl">{row_label_fn(label)}</td>{cells_html}</tr>')
    return rows_html


def _fob_variant_rows(variants, periods):
    """variants: [(label, bid_cells_dict, freight_cpb), ...] — one row per
    variant, ¢/bu = bid − freight."""
    vals = []
    for label, cells, frt in variants:
        row = [None if cells.get(p, {}).get("bid") is None else cells[p]["bid"] - frt
               for p in periods]
        vals.append((label, row))
    return _variant_value_rows(vals)


def _origin_table_open(periods, ncols):
    html = ['<table class="sheet"><tbody><tr>', '<th class="lblhdr">Origin</th>']
    html += [f'<th>{p}</th>' for p in periods]
    html.append('</tr>')
    return html


def _bid_cells_prior_for(source, market, sel_date):
    """Like _bid_cells_for, but also returns the market's prior posting (for
    up/down coloring) — used by the per-tab raw corridor table."""
    if sel_date is None:
        return {}, None, None
    rows = _cached_all(source)
    dates_all = sorted({r["date"] for r in rows if r["market"] == market})
    dates_le = [d for d in dates_all if d <= sel_date]
    if not dates_le:
        return {}, None, None
    eff = dates_le[-1]
    cells = {r["period"]: r for r in rows if r["market"] == market and r["date"] == eff}
    earlier = [d for d in dates_all if d < eff]
    prior = ({r["period"]: r for r in rows if r["market"] == market and r["date"] == earlier[-1]}
             if earlier else None)
    return cells, eff, prior


def _raw_corridor_table(markets, sel_date):
    """The raw bid/offer grid for just the given market(s) — same styling as
    the Bids tab, but scoped to only this railroad's own corridor(s) so each
    tab is self-contained."""
    entries = []
    for m in markets:
        cells, eff, prior = _bid_cells_prior_for("manual", m, sel_date)
        if cells:
            entries.append((m, eff, cells, prior))
    if not entries:
        st.caption("No postings on or before this date yet.")
        return
    periods = _period_union(*[e[2] for e in entries])
    html = [_card_open(), '<table class="sheet"><tbody><tr>', '<th class="lblhdr">Corridor</th>']
    html += [f'<th>{p}</th>' for p in periods]
    html.append('</tr>')
    for m, eff, cells, prior in entries:
        rail = cells[next(iter(cells))].get("rail") or ""
        rcol = RAIL_COLORS.get(rail, "#64748b")
        asof = ''
        if eff != sel_date:
            yy, mo, dd = eff.split("-")
            asof = f'<span class="asof-chip">as of {int(mo)}/{int(dd)}</span>'
        label = RAIL_DISPLAY.get(m, m)
        html.append(f'<tr><td class="lbl">{label}'
                    f'<span class="rail-chip" style="background:{rcol}">{rail}</span>{asof}</td>')
        for p in periods:
            html.append(_cell_html(cells.get(p), prior))
        html.append('</tr>')
    html.append('</tbody></table>')
    html.append(_card_close())
    st.markdown(''.join(html), unsafe_allow_html=True)


def _state_best_row(origins, cells, field, periods):
    """Best (highest) FOB among the given origins, for one corridor/region, per period."""
    out = []
    for p in periods:
        bid = cells.get(p, {}).get("bid")
        if bid is None:
            out.append(None)
            continue
        best = None
        for o in origins:
            v = bid - o[field]
            if best is None or v > best:
                best = v
        out.append(best)
    return out


def _state_fob_table(rows, variant_fields, bid_cells_map, periods, state_key="state",
                      per_variant=False):
    """One row per state, one column per period. Each cell is the BEST
    (highest) FOB among every origin in that state for that corridor/region
    — an index, not any single origin's actual number.

    per_variant=False (NS's style): one combined row per state, best across
    every active region — mirrors NS's Highlighted Origins, which already
    collapses to a single best-region row per origin.
    per_variant=True (CSX's style): one row per state PER active corridor
    (e.g. "via Columbus" / "via Evansville"), the better one tinted — mirrors
    CSX's Highlighted Origins, which compares corridors side by side."""
    if not variant_fields or not periods:
        st.caption("Select at least one corridor/region above to see this table.")
        return
    by_state = {}
    for r in rows:
        by_state.setdefault(r[state_key], []).append(r)
    if not by_state:
        st.caption("No data to index by state yet.")
        return

    ncols = 1 + len(periods)
    html = [_card_open(), '<table class="sheet"><tbody><tr>', '<th class="lblhdr">State</th>']
    html += [f'<th>{p}</th>' for p in periods]
    html.append('</tr>')
    for s in sorted(by_state):
        origins = by_state[s]
        if per_variant:
            label_rows = [(label, _state_best_row(origins, bid_cells_map[label], field, periods))
                          for label, field in variant_fields]
            html.append(f'<tr class="origin-hdr"><td colspan="{ncols}">{s}</td></tr>')
            html.extend(_variant_value_rows(label_rows, cell_fn=_fob_cell_int))
        else:
            vals = [None] * len(periods)
            for label, field in variant_fields:
                row = _state_best_row(origins, bid_cells_map[label], field, periods)
                for i, v in enumerate(row):
                    if v is not None and (vals[i] is None or v > vals[i]):
                        vals[i] = v
            cells = ''.join(f'<td>{round(v):+d}</td>' if v is not None else '<td>—</td>' for v in vals)
            html.append(f'<tr><td class="lbl">{s}</td>{cells}</tr>')
    html.append('</tbody></table>')
    html.append(_card_close())
    st.markdown(''.join(html), unsafe_allow_html=True)
    if per_variant:
        st.caption("Best (highest) FOB among every origin in that state, per corridor, per "
                   "period — blue = the better corridor for that state/period, same "
                   "comparison style as Highlighted Origins below.")
    else:
        st.caption("Best (highest) FOB among every origin in that state, per period — "
                   "an index, not any single origin's actual number.")


def _csx_tab(sel_date):
    st.caption(f"Posting date **{sel_date}** — change it on the 📋 Bids tab.")
    fc, fe = st.columns(2)
    show_col = fc.checkbox("Columbus", value=True, key="csx_f_col")
    show_evv = fe.checkbox("Evansville", value=True, key="csx_f_evv")
    if not show_col and not show_evv:
        st.info("Select at least one corridor to filter on.")
        return
    rows = FD.load_csx()

    col_cells, col_eff = _bid_cells_for("manual", "CSX Columbus", sel_date) if show_col else ({}, None)
    evv_cells, evv_eff = _bid_cells_for("manual", "CSX Evansville", sel_date) if show_evv else ({}, None)
    periods = _period_union(col_cells, evv_cells)
    asof_bits = []
    if col_eff and col_eff != sel_date:
        asof_bits.append(f"Columbus as of {col_eff}")
    if evv_eff and evv_eff != sel_date:
        asof_bits.append(f"Evansville as of {evv_eff}")

    active_markets = ([("CSX Columbus", col_cells)] if show_col else []) + \
                      ([("CSX Evansville", evv_cells)] if show_evv else [])
    st.markdown("### Rail FOB — CSX")
    _raw_corridor_table([m for m, _ in active_markets], sel_date)

    st.markdown("### FOB Index by State")
    variant_fields = ([("Columbus", "columbus_cpb")] if show_col else []) + \
                      ([("Evansville", "eville_altkyla_cpb")] if show_evv else [])
    bid_cells_map = {"Columbus": col_cells, "Evansville": evv_cells}
    _state_fob_table(rows, variant_fields, bid_cells_map, periods, per_variant=True)

    st.markdown("### Highlighted Origins")
    if asof_bits:
        st.caption(" · ".join(asof_bits))
    highlighted = [r for r in rows if r["highlighted"]]
    if periods and highlighted:
        ncols = 1 + len(periods)
        html = [_card_open()] + _origin_table_open(periods, ncols)
        flagged = []
        for r in highlighted:
            variants = []
            if show_col:
                variants.append(("Columbus", col_cells, r["columbus_cpb"]))
            if show_evv:
                variants.append(("Evansville", evv_cells, r["eville_altkyla_cpb"]))
                if r["eville_altkyla"] != r["eville_gafl"]:
                    flagged.append((_location_only(r["buying_station"]), r["eville_gafl_cpb"], r["eville_altkyla_cpb"]))
            star = " *" if show_evv and r["eville_altkyla"] != r["eville_gafl"] else ""
            frt_desc = " / ".join(f"{lbl} {v:.1f}¢" for lbl, _, v in variants)
            html.append(
                f'<tr class="origin-hdr"><td colspan="{ncols}">{r["state"]} · {_location_only(r["buying_station"])}'
                f'<span class="fut-sub"> &nbsp;freight {frt_desc}{star}</span></td></tr>'
            )
            html.extend(_fob_variant_rows(variants, periods))
        html.append('</tbody></table>')
        html.append(_card_close())
        st.markdown(''.join(html), unsafe_allow_html=True)
        if flagged:
            notes = "; ".join(f"{n} (GA/FL {g:+.1f}¢ vs AL/TN/KY/LA {a:+.1f}¢ used)"
                               for n, g, a in flagged)
            st.caption(f"* Evansville's rate depends on the unit train's downstream "
                       f"market — {notes}.")
    else:
        st.caption("No CSX Columbus/Evansville postings on or before this date yet.")

    with st.expander(f"All CSX origins, ranked by freight spread ({len(rows)} total)"):
        _expanded_freight_table(
            rows, state_key="state", label_cols=[
                ("Origin", lambda r: r["origin_group"]),
                ("Location", lambda r: _location_only(r["buying_station"])),
                ("Type", lambda r: r["train_type"]),
            ],
            variants=[("Columbus", "columbus_cpb", show_col), ("Evansville", "eville_altkyla_cpb", show_evv)],
        )

    st.markdown(
        '<div class="legend">FOB(origin) = bid − rail freight to that buying station '
        '(¢/bu = $/car ÷ 3500 bu/car × 100). Freight is a static reference rate from the '
        'CSX origin-spread workbook — only the bid side is live/archived. Highlighted = '
        'the origins starred in that workbook; <span class="sw bt"></span>blue = the '
        'better-netback corridor for that origin/period.</div>',
        unsafe_allow_html=True,
    )


def _ns_tab(sel_date):
    st.caption(f"Posting date **{sel_date}** — change it on the 📋 Bids tab.")
    cols = st.columns(3)
    show = {}
    for (region, field), c in zip(FD.NS_REGIONS.items(), cols):
        show[field] = c.checkbox(region, value=True, key=f"ns_f_{field}")
    active = [(region, field) for region, field in FD.NS_REGIONS.items() if show[field]]
    if not active:
        st.info("Select at least one region to filter on.")
        return
    rows = FD.load_ns()

    ftw_cells, ftw_eff = _bid_cells_for("manual", FD.NS_BID_MARKET, sel_date)
    periods = _period_union(ftw_cells)

    st.markdown("### Rail FOB — NS")
    _raw_corridor_table([FD.NS_BID_MARKET], sel_date)

    st.markdown("### FOB Index by State")
    variant_fields = [(region, field + "_cpb") for region, field in active]
    bid_cells_map = {region: ftw_cells for region, _ in active}
    _state_fob_table(rows, variant_fields, bid_cells_map, periods)

    st.markdown("### Highlighted Origins")
    if ftw_eff and ftw_eff != sel_date:
        st.caption(f"{FD.NS_BID_MARKET} as of {ftw_eff}")
    highlighted = [r for r in rows if r["highlighted"]]
    if periods and highlighted:
        ncols = 1 + len(periods)
        html = [_card_open()] + _origin_table_open(periods, ncols)
        for r in highlighted:
            variants = [(region, ftw_cells, r[f"{field}_cpb"]) for region, field in active]
            # All three regions net against the SAME NS Ft Wayne bid, so the
            # cheapest-freight region is the best one for every period, not
            # just some — default to showing just that one row, not all 3.
            best = min(variants, key=lambda v: v[2])
            frt_desc = f"{best[0]} {best[2]:.1f}¢"
            flag = ' <span class="fut-sub">(105-car eligible)</span>' if r["flag_105"] else ""
            html.append(
                f'<tr class="origin-hdr"><td colspan="{ncols}">{r["state"]} · {r["origin"]}'
                f'<span class="fut-sub"> &nbsp;best freight {frt_desc}</span>{flag}</td></tr>'
            )
            html.extend(_fob_variant_rows([best], periods))
        html.append('</tbody></table>')
        html.append(_card_close())
        st.markdown(''.join(html), unsafe_allow_html=True)
    else:
        st.caption(f"No {FD.NS_BID_MARKET} postings on or before this date yet.")

    with st.expander(f"All NS origins, ranked by freight spread ({len(rows)} total)"):
        _expanded_freight_table(
            rows, state_key="state",
            label_cols=[("Origin", lambda r: r["origin"]),
                        ("105-car", lambda r: "Y" if r["flag_105"] else "")],
            variants=[(region, field + "_cpb", show[field]) for region, field in FD.NS_REGIONS.items()],
        )

    st.markdown(
        '<div class="legend">FOB(origin) = bid at NS Ft Wayne − rail freight (¢/bu, '
        'already $/bu in the source workbook × 100). GA / NC-SC-VA / East are three '
        'published through-rate variants against the same physical move, all pricing '
        'off the same bid — so Highlighted Origins defaults to just the cheapest-freight '
        'region among whichever are checked above, not all three; see the expander below '
        'to compare regions side by side.</div>',
        unsafe_allow_html=True,
    )


def _bn_variant_row(cells, month_rates_cpb, periods):
    """¢/bu per period = bid − freight, but freight only exists for a period
    whose first named month falls in BN's currently-published rolling
    window (whatever months that is right now) — everything else is None
    (no roll, no guessing)."""
    row = []
    for p in periods:
        bid = cells.get(p, {}).get("bid")
        frt = FD.bn_freight_cpb(month_rates_cpb, p)
        row.append(None if bid is None or frt is None else bid - frt)
    return row


def _bn_state_best_row(origins, cells, field, periods):
    out = []
    for p in periods:
        bid = cells.get(p, {}).get("bid")
        if bid is None:
            out.append(None)
            continue
        best = None
        for o in origins:
            frt = FD.bn_freight_cpb(o[field], p)
            if frt is None:
                continue
            v = bid - frt
            if best is None or v > best:
                best = v
        out.append(best)
    return out


def _bn_tab(sel_date):
    st.caption(f"Posting date **{sel_date}** — change it on the 📋 Bids tab.")
    fc, fe = st.columns(2)
    show = {}
    for (dest, spec), c in zip(FD.BN_DESTINATIONS.items(), (fc, fe)):
        show[dest] = c.checkbox(dest, value=True, key=f"bn_f_{spec['field']}")
    active = [(dest, spec) for dest, spec in FD.BN_DESTINATIONS.items() if show[dest]]
    if not active:
        st.info("Select at least one destination to filter on.")
        return
    rows = FD.load_bn()
    published_months = sorted({m for r in rows for spec in FD.BN_DESTINATIONS.values()
                                for m in r[spec["field"] + "_cpb"]}, key=FD.bn_month_sort_key)
    published_disp = "/".join(m.upper() if m == "jj" else m.title() for m in published_months)

    cells_by_dest, eff_by_dest = {}, {}
    for dest, spec in active:
        cells_by_dest[dest], eff_by_dest[dest] = _bid_cells_for("manual", spec["market"], sel_date)
    periods = _period_union(*cells_by_dest.values())
    asof_bits = [f"{dest} as of {eff_by_dest[dest]}" for dest, _ in active
                 if eff_by_dest[dest] and eff_by_dest[dest] != sel_date]

    st.markdown("### Rail FOB — BN")
    _raw_corridor_table([spec["market"] for _, spec in active], sel_date)

    st.markdown("### FOB Index by State")
    if periods:
        by_state = {}
        for r in rows:
            by_state.setdefault(r["state"], []).append(r)
        ncols = 1 + len(periods)
        html = [_card_open(), '<table class="sheet"><tbody><tr>', '<th class="lblhdr">State</th>']
        html += [f'<th>{p}</th>' for p in periods]
        html.append('</tr>')
        for s in sorted(by_state):
            origins = by_state[s]
            label_rows = [(dest, _bn_state_best_row(origins, cells_by_dest[dest], spec["field"] + "_cpb", periods))
                          for dest, spec in active]
            html.append(f'<tr class="origin-hdr"><td colspan="{ncols}">{s}</td></tr>')
            html.extend(_variant_value_rows(label_rows, cell_fn=_fob_cell_int))
        html.append('</tbody></table>')
        html.append(_card_close())
        st.markdown(''.join(html), unsafe_allow_html=True)
        st.caption("Best (highest) FOB among every origin in that state, per destination, per "
                   f"period — blue = the better destination for that state/period. Only "
                   f"periods whose first named month is currently published ({published_disp}) "
                   "show a value.")

    st.markdown("### BN Origins")
    if asof_bits:
        st.caption(" · ".join(asof_bits))
    if periods:
        ncols = 1 + len(periods)
        html = [_card_open()] + _origin_table_open(periods, ncols)
        for r in rows:
            label_rows = [(dest, _bn_variant_row(cells_by_dest[dest], r[spec["field"] + "_cpb"], periods))
                          for dest, spec in active]
            html.append(
                f'<tr class="origin-hdr"><td colspan="{ncols}">{r["state"]} · {r["origin"]}'
                f'<span class="fut-sub"> &nbsp;freight published for {published_disp}</span></td></tr>'
            )
            html.extend(_variant_value_rows(label_rows))
        html.append('</tbody></table>')
        html.append(_card_close())
        st.markdown(''.join(html), unsafe_allow_html=True)
    else:
        st.caption("No BN PNW/Hereford postings on or before this date yet.")

    st.markdown(
        '<div class="legend">FOB(origin) = bid at BN PNW/Hereford − rail freight (¢/bu = '
        '$/car ÷ 4000 bu/car × 100). Unlike CSX/NS, BN publishes rates for a rolling ~4-month '
        f'window rather than one flat number — currently <b>{published_disp}</b> — a period '
        'nets against freight only when its first named month falls in that window; '
        'everything else shows "—" until the workbook rolls forward (re-run the extraction '
        'against a freshly saved copy to pick up the new months). All 11 BN origins are '
        'shown (the workbook has no separate highlighted subset for this railroad). Blue = '
        'the better destination for that origin/period.</div>',
        unsafe_allow_html=True,
    )


def _expanded_freight_table(rows, state_key, label_cols, variants):
    """Sortable reference table: one row per origin, one column per active
    freight variant (¢/bu), ranked cheapest-first across whichever variants
    are active. `variants`: [(label, cpb_field, is_active), ...]."""
    active = [(lbl, f) for lbl, f, on in variants if on]
    if not active:
        st.caption("Select at least one corridor/region above to see this list.")
        return

    def sort_key(r):
        return min(r[f] for _, f in active)

    ordered = sorted(rows, key=sort_key)
    html = [_card_open(), '<table class="sheet"><tbody><tr>',
            '<th class="lblhdr">State</th>']
    html += [f'<th class="lblhdr">{lbl}</th>' for lbl, _ in label_cols]
    html += [f'<th>{lbl} ¢/bu</th>' for lbl, _ in active]
    if len(active) > 1:
        html.append('<th class="lblhdr">Best</th>')
    html.append('</tr>')
    for r in ordered:
        cells = [f'<td class="lbl">{r[state_key]}</td>']
        cells += [f'<td class="lbl">{fn(r)}</td>' for _, fn in label_cols]
        cells += [f'<td>{r[f]:+.1f}</td>' for _, f in active]
        if len(active) > 1:
            best_lbl = min(active, key=lambda lf: r[lf[1]])[0]
            cells.append(f'<td class="lbl">{best_lbl}</td>')
        html.append('<tr>' + ''.join(cells) + '</tr>')
    html.append('</tbody></table>')
    html.append(_card_close())
    st.markdown(''.join(html), unsafe_allow_html=True)
    st.caption(f"{len(ordered)} locations, ranked cheapest freight first.")


REFERENCES = [
    ("CN GeoMapGuide — interactive rail network map", "https://cnebusiness.geomapguide.ca/"),
    ("NS Grain Customer Directory", "http://www.nscorp.com/content/nscorp/en/shipping-options/agriculture-and-forest-products/grain-customer-directory.html"),
    ("CSX Publications & Tariffs", "https://www.csx.com/index.cfm/customers/publications-tariffs/"),
    ("UP Shuttle Train Programs", "https://www.up.com/customers/bulk/shuttle/index.htm"),
    ("BNSF Grain Shuttle Facilities", "http://www.bnsf.com/customers/grain-facilities/shuttles/"),
    ("Rail Rate Checker — Useful Railroad Links", "https://www.railratechecker.com/Useful%20Railroad%20Links.html"),
    ("USDA AgTransport — Grain Rail Cars Loaded and Billed",
     "https://agtransport.usda.gov/Rail/Grain-Rail-Cars-Loaded-and-Billed/27k8-utc2/explore/query/"
     "SELECT%0A%20%20%60date%60%2C%0A%20%20%60week%60%2C%0A%20%20%60month%60%2C%0A%20%20%60year%60%2C%0A"
     "%20%20%60railroad%60%2C%0A%20%20%60state%60%2C%0A%20%20%60all%60%2C%0A%20%20%60dedicated_or_shuttle%60"
     "%2C%0A%20%20%60other%60%2C%0A%20%20%60state_point%60%0AORDER%20BY%20%60date%60%20DESC%20NULL%20FIRST/page/filter"),
]


def _map_tab():
    st.markdown("### CN Rail Network Map")
    st.caption("Live embed of CN's GeoMapGuide. If it doesn't load (some networks block "
               "third-party embeds), use the link below to open it directly.")
    components.iframe("https://cnebusiness.geomapguide.ca/", height=750, scrolling=True)
    st.markdown(
        '<div style="margin-top:8px">'
        '<a href="https://cnebusiness.geomapguide.ca/" target="_blank" '
        'style="color:#0693e3;font-weight:600">Open CN GeoMapGuide in a new tab ↗</a>'
        '</div>',
        unsafe_allow_html=True,
    )


def _references_tab():
    st.markdown("### Reference Links")
    html = [_card_open(), '<table class="sheet"><tbody>']
    for label, url in REFERENCES:
        html.append(
            f'<tr><td class="lbl" style="white-space:normal">'
            f'<a href="{url}" target="_blank" style="color:#0693e3;font-weight:600">{label}</a>'
            f'<br><span class="fut-sub">{url}</span></td></tr>'
        )
    html.append('</tbody></table>')
    html.append(_card_close())
    st.markdown(''.join(html), unsafe_allow_html=True)


bids_tab, csx_tab, ns_tab, bn_tab, map_tab, refs_tab = st.tabs(
    ["📋 Bids", "🚂 CSX", "🚂 NS", "🚂 BN", "🗺️ Map", "🔗 References"])

with bids_tab:
    st.markdown("### Manual Rail Corridors (chat-fed)")
    _manual_date = _sheet_board("manual", MANUAL_SECTIONS, "man", other_keep=set())

with csx_tab:
    _csx_tab(_manual_date)

with ns_tab:
    _ns_tab(_manual_date)

with bn_tab:
    _bn_tab(_manual_date)

with map_tab:
    _map_tab()

with refs_tab:
    _references_tab()

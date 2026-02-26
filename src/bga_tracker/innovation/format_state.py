"""
Innovation Game State Summary Formatter

Reads game_state.json and produces summary.html showing
hidden information from both perspectives, with card images.

Usage: python -m bga_tracker.innovation.format_state TABLE_ID

Input:  data/<TABLE_ID>/game_state.json + .env for PLAYER_NAME
Output: data/<TABLE_ID>/summary.html
"""

import json
import os
import re
import sys
from html import escape as esc
from pathlib import Path

from bga_tracker import PROJECT_ROOT

DATA_DIR = PROJECT_ROOT / "data"

# Relative paths from summary.html (data/<TABLE_ID>/) to assets/
ICONS_REL = "../../assets/icons"
CARDS_REL = "../../assets/cards"

# Load .env manually (no external deps)
_env_path = PROJECT_ROOT / ".env"
if _env_path.exists():
    with open(_env_path) as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _v = _line.split("=", 1)
                os.environ.setdefault(_k.strip(), _v.strip())

PERSPECTIVE = os.environ.get("PLAYER_NAME")
if not PERSPECTIVE:
    print("ERROR: PLAYER_NAME not set in .env or environment")
    sys.exit(1)

# Default section visibility
DEFAULT_BASE_DECK = os.environ.get("DEFAULT_BASE_DECK", "show").lower()
DEFAULT_CITIES_DECK = os.environ.get("DEFAULT_CITIES_DECK", "hide").lower()
DEFAULT_BASE_LIST = os.environ.get("DEFAULT_BASE_LIST", "none").lower()
DEFAULT_CITIES_LIST = os.environ.get("DEFAULT_CITIES_LIST", "none").lower()
DEFAULT_BASE_LAYOUT = os.environ.get("DEFAULT_BASE_LAYOUT", "wide").lower()
DEFAULT_CITIES_LAYOUT = os.environ.get("DEFAULT_CITIES_LAYOUT", "wide").lower()
DEFAULT_ACHIEVEMENTS = os.environ.get("DEFAULT_ACHIEVEMENTS", "show").lower()
DEFAULT_ACH_LAYOUT = os.environ.get("DEFAULT_ACH_LAYOUT", "wide").lower()

# Section placement: column.position
_SECTION_KEYS = [
    "HAND_OPPONENT", "HAND_ME", "SCORE_OPPONENT", "SCORE_ME",
    "ACHIEVEMENTS", "BASE_DECK", "CITIES_DECK", "BASE_LIST", "CITIES_LIST",
]
_SECTION_DEFAULTS = {k: f"1.{i+1}" for i, k in enumerate(_SECTION_KEYS)}
SECTION_POS = {}
for _k in _SECTION_KEYS:
    _val = os.environ.get(f"SECTION_{_k}", _SECTION_DEFAULTS[_k])
    _parts = _val.split(".", 1)
    SECTION_POS[_k] = (int(_parts[0]), float(_val))

# Color letter → full name mapping
COLOR_LETTER = {"B": "blue", "R": "red", "G": "green", "Y": "yellow", "P": "purple"}
COLOR_ORDER = {"blue": 0, "red": 1, "green": 2, "yellow": 3, "purple": 4}  # BRGYP

# Icon position mapping (from isotropic Rg = [0, 5, 4, 1, 2, 3])
# Top row:    icons[0]  icons[5]  icons[4]
# Bottom row: icons[1]  icons[2]  icons[3]
TOP_POSITIONS = [0, 5, 4]
BOT_POSITIONS = [1, 2, 3]

# Eye icons for Hidden/Revealed labels
ICON_EYE_OPEN = '<svg viewBox="0 0 24 24"><path d="M12 4.5C7 4.5 2.73 7.61 1 12c1.73 4.39 6 7.5 11 7.5s9.27-3.11 11-7.5c-1.73-4.39-6-7.5-11-7.5zm0 12.5c-2.76 0-5-2.24-5-5s2.24-5 5-5 5 2.24 5 5-2.24 5-5 5zm0-8c-1.66 0-3 1.34-3 3s1.34 3 3 3 3-1.34 3-3-1.34-3-3-3z"/></svg>'
ICON_EYE_CLOSED = '<svg viewBox="0 0 24 24"><path d="M12 7c2.76 0 5 2.24 5 5 0 .65-.13 1.26-.36 1.83l2.92 2.92c1.51-1.26 2.7-2.89 3.43-4.75-1.73-4.39-6-7.5-11-7.5-1.4 0-2.74.25-3.98.7l2.16 2.16C11.74 7.13 11.35 7 12 7zM2 4.27l2.28 2.28.46.46A11.8 11.8 0 001 12c1.73 4.39 6 7.5 11 7.5 1.55 0 3.03-.3 4.38-.84l.42.42L19.73 22 21 20.73 3.27 3 2 4.27zM7.53 9.8l1.55 1.55c-.05.21-.08.43-.08.65 0 1.66 1.34 3 3 3 .22 0 .44-.03.65-.08l1.55 1.55c-.67.33-1.41.53-2.2.53-2.76 0-5-2.24-5-5 0-.79.2-1.53.53-2.2zm4.31-.78l3.15 3.15.02-.16c0-1.66-1.34-3-3-3l-.17.01z"/></svg>'
_DOGMA_IMG_RE = re.compile(r'<img\s+src="/static/icons/inline-(\w+)\.png"\s*/?>')

# --- Card info loading ---

_cardinfo = None
_card_by_name = None


def _load_cardinfo():
    global _cardinfo, _card_by_name
    if _cardinfo is not None:
        return
    with open(PROJECT_ROOT / "assets" / "cardinfo.json") as f:
        _cardinfo = json.load(f)
    _card_by_name = {}
    for idx, card in enumerate(_cardinfo):
        if card and card.get("name"):
            card["cardnum"] = idx
            _card_by_name[card["name"]] = card


def get_card(name):
    """Look up card by name. Returns card dict or None."""
    _load_cardinfo()
    return _card_by_name.get(name)


# --- HTML helpers ---

def clean_dogma(dogma_list):
    """Clean dogma HTML for tooltip text."""
    if not dogma_list:
        return ""
    lines = []
    for d in dogma_list:
        # Replace inline icon images with text names
        text = _DOGMA_IMG_RE.sub(lambda m: m.group(1), d)
        # Strip remaining HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        # Normalize whitespace
        text = ' '.join(text.split())
        lines.append(text)
    return '\n'.join(lines)


def icon_img(icon_name, card_color, cardnum=None):
    """Generate <img> tag for a single icon."""
    if icon_name == "hex":
        src = f"{ICONS_REL}/hex_{cardnum}.png"
    elif icon_name in ("left", "right", "up"):
        src = f"{ICONS_REL}/arrow_{card_color}.png"
    elif icon_name.startswith("bonus-"):
        num = icon_name.split("-")[1]
        src = f"{ICONS_REL}/bonus_{num}.png"
    else:
        # crown, leaf, lightbulb, castle, factory, clock, blackflag, whiteflag, plus
        src = f"{ICONS_REL}/{icon_name}_{card_color}.png"
    return f'<img src="{src}" width="20" height="20" alt="{esc(icon_name)}">'


def render_card(name, age, color_letter, star=False, is_deck=False):
    """Render a card as a colored div. Layout depends on card set.

    Set 0 (base) — 2×3 grid:
        +----------+---------------------+
        | icons[0] | Card Name           |  row 1 (cols 2+3 merged)
        +----------+------------+--------+
        | icons[1] | icons[2,3] |  6 *   |  row 2
        +----------+------------+--------+

    Set 3 (cities) — 2×2 grid, icons only (name in tooltip):
        +---------------------+--------+
        | [0]  [5]  [4]       |        |
        +---------------------+--------+
        | [1]  [2]  [3]       |  6     |
        +---------------------+--------+
    """
    color_name = COLOR_LETTER.get(color_letter, "blue")
    card = get_card(name)
    age_cls = "card-age starred" if star else "card-age"

    # Dogma tooltip
    dogma_text = clean_dogma(card.get("dogmas")) if card else ""
    tooltip_attr = f' data-tooltip="{esc(dogma_text)}"' if dogma_text else ""

    if not card or card.get("set") not in (0, 3):
        # Fallback: simple card
        return (
            f'<div class="card b-{color_name}"{tooltip_attr}>'
            f'<div class="card-name">{esc(name)}</div>'
            f'<div class="card-body"><div class="{age_cls}">{age}</div></div>'
            f'</div>'
        )

    cardnum = card["cardnum"]
    icons = card.get("icons", [])
    img = lambda i: icon_img(icons[i], color_name, cardnum) if i < len(icons) else ""

    if card["set"] == 0 and len(icons) == 4:
        # Base card: 2×3 CSS grid with image tooltip
        tip = f'<div class="card-tip"><img src="{CARDS_REL}/card_{cardnum}.png"></div>'
        return (
            f'<div class="card card-base b-{color_name}">'
            f'<div class="cb-tl">{img(0)}</div>'
            f'<div class="cb-name">{esc(name)}</div>'
            f'<div class="cb-bl">{img(1)}</div>'
            f'<div class="cb-mid">{img(2)}{img(3)}</div>'
            f'<div class="{age_cls}">{age}</div>'
            f'{tip}'
            f'</div>'
        )
    else:
        # Cities card: 2×2 CSS grid — icons only, name in tooltip
        top_icons = "".join(img(p) for p in TOP_POSITIONS if p < len(icons))
        bot_icons = "".join(img(p) for p in BOT_POSITIONS if p < len(icons))
        tip_text = f"{esc(name)}\n{esc(dogma_text)}" if dogma_text else esc(name)
        tip = f'<div class="card-tip-text">{tip_text}</div>'
        return (
            f'<div class="card card-cities b-{color_name}">'
            f'<div class="cc-top">{top_icons}</div>'
            f'<div class="cc-bot">{bot_icons}</div>'
            f'<div class="{age_cls}">{age}</div>'
            f'{tip}'
            f'</div>'
        )


def render_unknown(age=None, card_set=None):
    """Render a single hidden card, same size as a regular base card."""
    display_age = age if age is not None else ""
    if card_set == "b":
        cls = "b-gray-base"
    elif card_set == "c":
        cls = "b-gray-cities"
    else:
        cls = "b-gray"
    return (
        f'<div class="card card-base {cls}">'
        f'<div class="cb-tl"></div>'
        f'<div class="cb-name"></div>'
        f'<div class="cb-bl"></div>'
        f'<div class="cb-mid"></div>'
        f'<div class="card-age">{display_age}</div>'
        f'</div>'
    )


# --- Section formatters ---

def find_players(state):
    """Derive my player and opponent from state board keys + PERSPECTIVE."""
    players = list(state["board"].keys())
    if PERSPECTIVE not in players:
        print(f"ERROR: PLAYER_NAME '{PERSPECTIVE}' not found in board players: {players}")
        sys.exit(1)
    opponent = [p for p in players if p != PERSPECTIVE][0]
    return PERSPECTIVE, opponent


def _format_deck(actual_deck, key):
    """Format a deck section (base or cities) as card divs per age."""
    age = 1
    while age <= 10 and not actual_deck.get(str(age), {}).get(key, []):
        age += 1

    rows = []
    for age in range(age, 11):
        entries = actual_deck.get(str(age), {}).get(key, [])
        cards_html = []
        for entry in entries:
            if entry is None:
                cards_html.append(render_unknown())
            else:
                name = entry["name"]
                card = get_card(name)
                if card:
                    color_letter = _COLOR_TO_LETTER.get(card["color"], "B")
                    cards_html.append(render_card(name, age, color_letter, star=entry.get("revealed", False), is_deck=True))
                else:
                    cards_html.append(render_unknown())

        row_content = "".join(cards_html) if cards_html else ""
        rows.append(
            f'<div class="deck-age">'
            f'<span class="deck-age-label">{age}</span>'
            f'<div class="card-row">{row_content}</div>'
            f'</div>'
        )
    return "\n".join(rows)


def format_deck_section(actual_deck):
    return _format_deck(actual_deck, "base")


def format_cities_section(actual_deck):
    return _format_deck(actual_deck, "cities")


_COLOR_TO_LETTER = {"blue": "B", "red": "R", "green": "G", "yellow": "Y", "purple": "P"}
_COLOR_NAMES_ORDERED = ["blue", "red", "green", "yellow", "purple"]  # BRGYP


def _render_card_with_known(card, known_names):
    """Render a card and mark it with data-known if in known_names."""
    color_letter = _COLOR_TO_LETTER.get(card["color"], "B")
    html = render_card(card["name"], card["age"], color_letter)
    if known_names is not None and card["name"] in known_names:
        html = html.replace('<div class="card ', '<div data-known class="card ', 1)
    return html


def _all_known(cards, known_names):
    """Check if all cards in a list are in known_names."""
    return known_names is not None and all(c["name"] in known_names for c in cards)


def _format_all_wide(cards_by_age, known_names):
    """Wide layout: one row per age, all cards in a line."""
    rows = []
    for age in range(1, 11):
        cards = sorted(cards_by_age.get(age, []),
                       key=lambda c: (COLOR_ORDER.get(c["color"], 99), c["name"]))
        if not cards:
            continue
        cards_html = [_render_card_with_known(c, known_names) for c in cards]
        all_known_cls = " all-known" if _all_known(cards, known_names) else ""
        rows.append(
            f'<div class="deck-age{all_known_cls}">'
            f'<span class="deck-age-label">{age}</span>'
            f'<div class="card-row">{"".join(cards_html)}</div>'
            f'</div>'
        )
    return "\n".join(rows)


def _format_all_tall(cards_by_age, known_names):
    """Tall layout: 5 color columns (BRGYP), age label on the left."""
    # Group cards by (age, color) -> sorted list
    grid = {}  # (age, color) -> [card, ...]
    for age in range(1, 11):
        for card in cards_by_age.get(age, []):
            grid.setdefault((age, card["color"]), []).append(card)
    for k in grid:
        grid[k].sort(key=lambda c: c["name"])

    rows = []
    for age in range(1, 11):
        # Find max cards per color at this age (= number of sub-rows)
        max_per_color = max(
            (len(grid.get((age, color), [])) for color in _COLOR_NAMES_ORDERED), default=0)
        if max_per_color == 0:
            continue

        all_age_cards = [c for color in _COLOR_NAMES_ORDERED for c in grid.get((age, color), [])]
        all_known_cls = ' class="all-known"' if _all_known(all_age_cards, known_names) else ""

        age_rows = []
        for row_idx in range(max_per_color):
            cells = []
            for color in _COLOR_NAMES_ORDERED:
                color_cards = grid.get((age, color), [])
                if row_idx < len(color_cards):
                    cells.append(f'<td>{_render_card_with_known(color_cards[row_idx], known_names)}</td>')
                else:
                    cells.append('<td></td>')
            age_rows.append(f'<tr{all_known_cls}>{"".join(cells)}</tr>')

        # First row gets the age label with rowspan
        age_rows[0] = age_rows[0].replace(
            f'<tr{all_known_cls}>',
            f'<tr{all_known_cls}><td class="deck-age-label" rowspan="{max_per_color}">{age}</td>',
            1)

        rows.extend(age_rows)

    return f'<table class="tall-grid">{"".join(rows)}</table>'


def format_all_cards(card_set, known_names=None):
    """Format all cards of a given set. Returns (wide_html, tall_html)."""
    _load_cardinfo()
    cards_by_age = {}
    for card in _card_by_name.values():
        if card.get("set") != card_set:
            continue
        cards_by_age.setdefault(card["age"], []).append(card)

    wide = _format_all_wide(cards_by_age, known_names)
    tall = _format_all_tall(cards_by_age, known_names)
    return wide, tall


def format_opponent_zone(entries):
    """Format opponent's hand or score as card divs, sorted by age (known before unknown)."""
    if not entries:
        return '<div class="hand-row"><span class="row-label"> </span><div class="card-row"><div class="empty-card">empty</div></div></div>'
    # Parse entries into (age, is_unknown, html) tuples for sorting
    parsed = []
    for entry in entries:
        name = entry.get("name")
        if name:
            card = get_card(name)
            if card:
                age = card["age"]
                color_letter = _COLOR_TO_LETTER.get(card["color"], "B")
                parsed.append((age, 0, render_card(name, age, color_letter)))
            else:
                parsed.append((0, 1, render_unknown()))
        else:
            age = entry.get("age", 0)
            card_set = "b" if entry.get("set") == 0 else "c" if entry.get("set") == 3 else None
            parsed.append((age, 1, render_unknown(age if age else None, card_set)))
    parsed.sort(key=lambda x: (x[0], x[1]))
    cards = [html for _, _, html in parsed]
    return f'<div class="hand-row"><span class="row-label"> </span><div class="card-row">{"".join(cards)}</div></div>'


def format_my_zone(entries):
    """Format my score as two rows: hidden and revealed."""
    if not entries:
        return '<div class="card-row"><div class="empty-card">empty</div></div>'
    revealed = []
    hidden = []
    for entry in entries:
        name = entry.get("name")
        if not name:
            # Unknown card
            age = entry.get("age")
            card_set = "b" if entry.get("set") == 0 else "c" if entry.get("set") == 3 else None
            hidden.append(render_unknown(age, card_set))
            continue
        card = get_card(name)
        if not card:
            hidden.append(render_unknown())
            continue
        color_letter = _COLOR_TO_LETTER.get(card["color"], "B")
        if entry.get("revealed"):
            revealed.append(render_card(name, card["age"], color_letter, star=True))
        else:
            hidden.append(render_card(name, card["age"], color_letter))

    if not revealed and not hidden:
        return '<div class="card-row"><div class="empty-card">empty</div></div>'

    parts = []
    if hidden:
        parts.append(
            f'<div class="hand-row">'
            f'<span class="row-label">{ICON_EYE_CLOSED}</span>'
            f'<div class="card-row">{"".join(hidden)}</div>'
            f'</div>'
        )
    if revealed:
        parts.append(
            f'<div class="hand-row">'
            f'<span class="row-label">{ICON_EYE_OPEN}</span>'
            f'<div class="card-row">{"".join(revealed)}</div>'
            f'</div>'
        )
    return "\n".join(parts)


def format_my_hand(entries):
    """Format my hand as two rows: hidden first, revealed second."""
    if not entries:
        return '<div class="card-row"><div class="empty-card">empty</div></div>'
    revealed = []
    hidden = []
    for entry in entries:
        name = entry.get("name")
        if not name:
            # Unknown card
            age = entry.get("age")
            card_set = "b" if entry.get("set") == 0 else "c" if entry.get("set") == 3 else None
            hidden.append(render_unknown(age, card_set))
            continue
        card = get_card(name)
        if not card:
            continue
        color_letter = _COLOR_TO_LETTER.get(card["color"], "B")
        is_revealed = entry.get("revealed", False)
        card_html = render_card(name, card["age"], color_letter, star=is_revealed)
        if is_revealed:
            revealed.append(card_html)
        else:
            hidden.append(card_html)

    if not revealed and not hidden:
        return '<div class="card-row"><div class="empty-card">empty</div></div>'

    parts = []
    if hidden:
        parts.append(
            f'<div class="hand-row">'
            f'<span class="row-label">{ICON_EYE_CLOSED}</span>'
            f'<div class="card-row">{"".join(hidden)}</div>'
            f'</div>'
        )
    if revealed:
        parts.append(
            f'<div class="hand-row">'
            f'<span class="row-label">{ICON_EYE_OPEN}</span>'
            f'<div class="card-row">{"".join(revealed)}</div>'
            f'</div>'
        )
    return "\n".join(parts)


def _tri_toggle(target_id, options, default):
    """Build a tri-toggle span and the initial style/class for the target div.

    options: list of (mode, label) pairs, e.g. [("none", "Hide"), ("all", "Show")]
    default: the env value that should be active initially.
             Aliases: "show" -> "all", "hide" -> "none".
    Returns (toggle_html, div_attrs) where div_attrs is the extra attributes string.
    """
    mode_aliases = {"show": "all", "hide": "none"}
    default_mode = mode_aliases.get(default, default)
    valid_modes = {m for m, _ in options}
    if default_mode not in valid_modes:
        default_mode = options[0][0]

    parts = []
    for i, (mode, label) in enumerate(options):
        active = " active" if mode == default_mode else ""
        parts.append(f'<span class="tri-opt{active}" data-mode="{mode}">{label}</span>')
        if i < len(options) - 1:
            parts.append('<span class="tri-sep">|</span>')
    toggle = f'<span class="tri-toggle" data-target="{target_id}">[{"".join(parts)}]</span>'

    attrs = ""
    if default_mode == "none":
        attrs += ' style="display:none"'
    if default_mode == "unknown":
        attrs += ' class="mode-unknown"'
    return toggle, attrs


# --- HTML template ---

HTML_TEMPLATE = """\
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Innovation &mdash; {table_id}</title>
<link href="https://fonts.googleapis.com/css2?family=Russo+One&family=Barlow+Condensed&display=swap" rel="stylesheet">
<style>
body {{
  background: #1e1e1e;
  color: #d4d4d4;
  font-family: Consolas, 'Courier New', monospace;
  font-size: 14px;
  padding: 20px;
}}

/* Multi-column page layout */
.page-grid {{ display: grid; gap: 20px; align-items: start; }}
.page-col {{ min-width: 0; }}

.section {{ margin-bottom: 12px; }}
.section-title {{ font-size: 13px; margin-bottom: 4px; font-weight: bold; color: #eee; }}
.dim {{ color: #666; }}
.empty-card {{ width: 92px; height: 49px; display: inline-flex; align-items: center; justify-content: center; color: #666; font-size: 12px; }}

/* Card — shared */
.card {{
  display: inline-block;
  padding: 2px;
  border-radius: 4px;
  border: 1px solid;
  margin: 1px;
  position: relative;
  vertical-align: top;
  cursor: default;
}}
.card.b-blue   {{ background: #1a3a5c; border-color: #4a9eff; color: #8ec8ff; }}
.card.b-red    {{ background: #5c1a1a; border-color: #ff4444; color: #ff8888; }}
.card.b-green  {{ background: #1a4c1a; border-color: #44bb44; color: #88dd88; }}
.card.b-yellow {{ background: #4c4a1a; border-color: #ccaa00; color: #eedd66; }}
.card.b-purple {{ background: #3a1a5c; border-color: #bb66ff; color: #dd99ff; }}
.card.b-gray   {{ background: #333; border-color: #555; color: #888; }}
.card.b-gray-base   {{ background: #363328; border-color: #6b6545; color: #999078; }}
.card.b-gray-cities {{ background: #362833; border-color: #6b4565; color: #997088; }}
.card img {{ width: 20px; height: 20px; display: block; }}

/* Set 0 (base) — 2×3 CSS grid */
.card-base {{
  display: inline-grid;
  grid-template-columns: 20px 41px 25px;
  grid-template-rows: 20px 20px;
  gap: 1px;
  align-items: center;
}}
.cb-tl   {{ grid-row: 1; grid-column: 1; }}
.cb-name {{ grid-row: 1; grid-column: 2 / 4; font-size: 12px; white-space: nowrap; font-family: 'Barlow Condensed', sans-serif; padding-left: 1px; color: #fff; }}
.cb-bl   {{ grid-row: 2; grid-column: 1; }}
.cb-mid  {{ grid-row: 2; grid-column: 2; display: flex; gap: 1px; justify-self: start; }}
.card-base > .card-age {{ grid-row: 2; grid-column: 3; align-self: center; justify-self: end; }}

/* Set 3 (cities) — 2×2 CSS grid, icons only */
.card-cities {{
  display: inline-grid;
  grid-template-columns: 62px 25px;
  grid-template-rows: 20px 20px;
  gap: 1px;
  align-items: center;
}}
.cc-top {{ grid-row: 1; grid-column: 1; display: flex; gap: 1px; }}
.cc-bot {{ grid-row: 2; grid-column: 1; display: flex; gap: 1px; }}
.card-cities > .card-age {{ grid-row: 2; grid-column: 2; align-self: center; justify-self: end; }}
.card-age {{
  font-family: 'Russo One', sans-serif;
  font-size: 18px;
  font-weight: bold;
  text-align: center;
  min-width: 20px;
  color: #fff;
}}
.card-age.starred {{ color: #ff4444; }}
.b-red .card-age.starred {{ color: #ff9999; }}

/* Image tooltip (base cards) */
.card-tip {{
  display: none;
  position: fixed;
  z-index: 10;
  pointer-events: none;
}}
.card-tip img {{ width: 375px; height: auto; border-radius: 6px; }}
.card:hover > .card-tip {{ display: block; }}

/* Text tooltip (cities cards) */
.card-tip-text {{
  display: none;
  position: fixed;
  z-index: 10;
  background: #222;
  color: #ccc;
  padding: 8px 10px;
  border-radius: 4px;
  font-size: 11px;
  white-space: pre-wrap;
  max-width: 320px;
  border: 1px solid #555;
  pointer-events: none;
  line-height: 1.4;
}}
.card:hover > .card-tip-text {{ display: block; }}

/* Layout */
.deck-age {{
  display: flex;
  align-items: flex-start;
  min-height: 49px;
  gap: 6px;
}}
.deck-age-label {{
  font-family: 'Russo One', sans-serif;
  font-size: 18px;
  font-weight: bold;
  color: #888;
  width: 24px;
  flex-shrink: 0;
  text-align: center;
  align-self: center;
}}
.age-label {{
  min-width: 24px;
  text-align: right;
  color: #888;
  font-size: 13px;
  padding-top: 6px;
}}
.card-row {{
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
}}
/* Tall grid layout */
.tall-grid {{ border-collapse: collapse; }}
.tall-grid td {{ padding: 0; vertical-align: top; }}
.tall-grid .deck-age-label {{ vertical-align: middle; padding-right: 6px; }}
.hand-row {{
  display: flex;
  align-items: flex-start;
  gap: 6px;
  margin-bottom: 4px;
}}
.row-label {{
  width: 24px;
  flex-shrink: 0;
  align-self: center;
  text-align: center;
}}
.row-label svg {{ width: 20px; height: 20px; fill: #888; }}
/* Tri-toggle (Hide | Show | None | All | Unknown) */
.tri-toggle {{ font-size: 12px; font-weight: normal; vertical-align: baseline; color: #aaa; }}
.tri-sep {{ color: #555; margin: 0 2px; }}
.tri-opt {{ cursor: pointer; color: #555; padding: 1px 3px; border-radius: 2px; }}
.tri-opt:hover {{ color: #bbb; }}
.tri-opt.active {{ color: #aaa; }}

/* Unknown mode: mask known cards to look like b-gray unknowns */
.mode-unknown [data-known] {{ background: #333 !important; border-color: #555 !important; color: #888 !important; }}
.mode-unknown [data-known] .cb-tl,
.mode-unknown [data-known] .cb-name,
.mode-unknown [data-known] .cb-bl,
.mode-unknown [data-known] .cb-mid,
.mode-unknown [data-known] .cc-top,
.mode-unknown [data-known] .cc-bot,
.mode-unknown [data-known] .card-age,
.mode-unknown [data-known] .card-tip,
.mode-unknown [data-known] .card-tip-text {{ visibility: hidden; }}
.mode-unknown .all-known {{ display: none; }}
</style>
</head>
<body>
{content}
<script>
document.addEventListener('mousemove', function(e) {{
  var tips = document.querySelectorAll('.card:hover > .card-tip, .card:hover > .card-tip-text');
  tips.forEach(function(tip) {{
    var rect = tip.getBoundingClientRect();
    var w = rect.width || 375, h = rect.height || 275;
    var x = e.clientX + 12;
    var y = e.clientY + 12;
    if (x + w > window.innerWidth) x = e.clientX - w - 12;
    if (y + h > window.innerHeight) y = e.clientY - h - 12;
    if (x < 0) x = 4;
    if (y < 0) y = 4;
    tip.style.left = x + 'px';
    tip.style.top = y + 'px';
  }});
}});
document.querySelectorAll('.tri-toggle').forEach(function(toggle) {{
  toggle.addEventListener('click', function(e) {{
    var opt = e.target.closest('.tri-opt');
    if (!opt) return;
    var mode = opt.getAttribute('data-mode');
    var target = document.getElementById(toggle.getAttribute('data-target'));
    if (!target) return;
    toggle.querySelectorAll('.tri-opt').forEach(function(o) {{ o.classList.remove('active'); }});
    opt.classList.add('active');
    if (mode === 'none') {{
      target.style.display = 'none';
      target.classList.remove('mode-unknown');
    }} else if (mode === 'all') {{
      target.style.display = '';
      target.classList.remove('mode-unknown');
    }} else if (mode === 'unknown') {{
      target.style.display = '';
      target.classList.add('mode-unknown');
    }} else if (mode === 'wide' || mode === 'tall') {{
      var id = toggle.getAttribute('data-target');
      document.querySelectorAll('.layout-wide[data-list="'+id+'"]').forEach(function(el) {{
        el.style.display = mode === 'wide' ? '' : 'none';
      }});
      document.querySelectorAll('.layout-tall[data-list="'+id+'"]').forEach(function(el) {{
        el.style.display = mode === 'tall' ? '' : 'none';
      }});
    }}
  }});
}});
</script>
</body>
</html>"""


def format_summary(state, table_id):
    """Assemble the full summary as HTML."""
    me, opponent = find_players(state)

    # Build sets of card names known to me, by set
    known_base = set()
    known_cities = set()

    def _add_known(name):
        card = get_card(name)
        if not card:
            return
        if card.get("set") == 0:
            known_base.add(name)
        elif card.get("set") == 3:
            known_cities.add(name)

    # My hand/score — all cards known to me
    for zone in ("hand", "score"):
        for entry in state.get(zone, {}).get(me, []):
            if "name" in entry:
                _add_known(entry["name"])
    # Opponent hand/score — only revealed cards
    for zone in ("hand", "score"):
        for entry in state.get(zone, {}).get(opponent, []):
            if entry.get("revealed") and "name" in entry:
                _add_known(entry["name"])
    # Board — all cards visible
    for player_entries in state.get("board", {}).values():
        for entry in player_entries:
            _add_known(entry["name"])
    # Deck — named cards (known position)
    for age_stacks in state.get("actual_deck", {}).values():
        for key in ("base", "cities"):
            for entry in age_stacks.get(key, []):
                if entry is not None:
                    _add_known(entry["name"])
    # Achievements — deduced cards
    for entry in state.get("achievements", []):
        if entry is not None:
            _add_known(entry["name"])

    # --- Build named sections ---
    named = {}

    named["HAND_OPPONENT"] = (
        f'<div class="section">'
        f'<div class="section-title">Hand &mdash; opponent</div>'
        f'{format_opponent_zone(state.get("hand", {}).get(opponent, []))}'
        f'</div>'
    )

    named["HAND_ME"] = (
        f'<div class="section">'
        f'<div class="section-title">Hand &mdash; me</div>'
        f'{format_my_hand(state.get("hand", {}).get(me, []))}'
        f'</div>'
    )

    opp_score = state.get("score", {}).get(opponent, [])
    named["SCORE_OPPONENT"] = (
        f'<div class="section">'
        f'<div class="section-title">Score &mdash; opponent</div>'
        f'{format_opponent_zone(opp_score)}'
        f'</div>'
    ) if opp_score else ""

    my_score = state.get("score", {}).get(me, [])
    named["SCORE_ME"] = (
        f'<div class="section">'
        f'<div class="section-title">Score &mdash; me</div>'
        f'{format_my_zone(my_score)}'
        f'</div>'
    ) if my_score else ""

    # Achievements (ages 1-9)
    ach_toggle, ach_attrs = _tri_toggle("achievements",
        [("none", "Hide"), ("all", "Show")], DEFAULT_ACHIEVEMENTS)
    achl_toggle, _ = _tri_toggle("achievements",
        [("wide", "Wide"), ("tall", "Tall")], DEFAULT_ACH_LAYOUT)
    ach_entries = state.get("achievements", [])
    ach_cards = []
    for i, entry in enumerate(ach_entries):
        age = i + 1
        if entry is None:
            ach_cards.append(render_unknown(age))
        else:
            card = get_card(entry["name"])
            if card:
                color_letter = _COLOR_TO_LETTER.get(card["color"], "B")
                ach_cards.append(render_card(entry["name"], card["age"], color_letter))
            else:
                ach_cards.append(render_unknown(age))
    # Pad to 9 if fewer entries
    for age in range(len(ach_entries) + 1, 10):
        ach_cards.append(render_unknown(age))
    # Wide: single row with spacer
    ach_wide = (
        f'<div class="hand-row">'
        f'<span class="row-label"> </span>'
        f'<div class="card-row">{"".join(ach_cards)}</div>'
        f'</div>'
    )
    # Tall: two rows of 5+4 with spacer
    ach_tall = (
        f'<div class="hand-row">'
        f'<span class="row-label"> </span>'
        f'<div class="card-row">{"".join(ach_cards[:5])}</div>'
        f'</div>'
        f'<div class="hand-row">'
        f'<span class="row-label"> </span>'
        f'<div class="card-row">{"".join(ach_cards[5:])}</div>'
        f'</div>'
    )
    ach_wide_hide = ' style="display:none"' if DEFAULT_ACH_LAYOUT == "tall" else ""
    ach_tall_hide = ' style="display:none"' if DEFAULT_ACH_LAYOUT != "tall" else ""
    named["ACHIEVEMENTS"] = (
        f'<div class="section">'
        f'<div class="section-title">Achievements {ach_toggle} {achl_toggle}</div>'
        f'<div id="achievements"{ach_attrs}>'
        f'<div class="layout-wide" data-list="achievements"{ach_wide_hide}>{ach_wide}</div>'
        f'<div class="layout-tall" data-list="achievements"{ach_tall_hide}>{ach_tall}</div>'
        f'</div>'
        f'</div>'
    )

    bd_toggle, bd_attrs = _tri_toggle("base-deck",
        [("none", "Hide"), ("all", "Show")], DEFAULT_BASE_DECK)
    named["BASE_DECK"] = (
        f'<div class="section">'
        f'<div class="section-title">Base deck {bd_toggle}</div>'
        f'<div id="base-deck"{bd_attrs}>{format_deck_section(state.get("actual_deck", {}))}</div>'
        f'</div>'
    )

    cd_toggle, cd_attrs = _tri_toggle("cities-deck",
        [("none", "Hide"), ("all", "Show")], DEFAULT_CITIES_DECK)
    named["CITIES_DECK"] = (
        f'<div class="section">'
        f'<div class="section-title">Cities deck {cd_toggle}</div>'
        f'<div id="cities-deck"{cd_attrs}>{format_cities_section(state.get("actual_deck", {}))}</div>'
        f'</div>'
    )

    bl_toggle, bl_attrs = _tri_toggle("base-list",
        [("none", "None"), ("all", "All"), ("unknown", "Unknown")], DEFAULT_BASE_LIST)
    bll_toggle, _ = _tri_toggle("base-list",
        [("wide", "Wide"), ("tall", "Tall")], DEFAULT_BASE_LAYOUT)
    base_wide, base_tall = format_all_cards(0, known_base)
    bl_wide_hide = ' style="display:none"' if DEFAULT_BASE_LAYOUT == "tall" else ""
    bl_tall_hide = ' style="display:none"' if DEFAULT_BASE_LAYOUT != "tall" else ""
    named["BASE_LIST"] = (
        f'<div class="section">'
        f'<div class="section-title">Base list {bl_toggle} {bll_toggle}</div>'
        f'<div id="base-list"{bl_attrs}>'
        f'<div class="layout-wide" data-list="base-list"{bl_wide_hide}>{base_wide}</div>'
        f'<div class="layout-tall" data-list="base-list"{bl_tall_hide}>{base_tall}</div>'
        f'</div>'
        f'</div>'
    )

    cl_toggle, cl_attrs = _tri_toggle("cities-list",
        [("none", "None"), ("all", "All"), ("unknown", "Unknown")], DEFAULT_CITIES_LIST)
    cll_toggle, _ = _tri_toggle("cities-list",
        [("wide", "Wide"), ("tall", "Tall")], DEFAULT_CITIES_LAYOUT)
    cities_wide, cities_tall = format_all_cards(3, known_cities)
    cl_wide_hide = ' style="display:none"' if DEFAULT_CITIES_LAYOUT == "tall" else ""
    cl_tall_hide = ' style="display:none"' if DEFAULT_CITIES_LAYOUT != "tall" else ""
    named["CITIES_LIST"] = (
        f'<div class="section">'
        f'<div class="section-title">Cities list {cl_toggle} {cll_toggle}</div>'
        f'<div id="cities-list"{cl_attrs}>'
        f'<div class="layout-wide" data-list="cities-list"{cl_wide_hide}>{cities_wide}</div>'
        f'<div class="layout-tall" data-list="cities-list"{cl_tall_hide}>{cities_tall}</div>'
        f'</div>'
        f'</div>'
    )

    # --- Arrange sections into columns ---
    # Group by column number, sort by position within each column
    columns = {}  # col_num -> [(pos, key, html)]
    list_sections = {"BASE_LIST", "CITIES_LIST"}
    for key, html in named.items():
        if not html:
            continue
        col_num, pos = SECTION_POS[key]
        columns.setdefault(col_num, []).append((pos, key, html))
    for col_num in columns:
        columns[col_num].sort()

    num_cols = max(columns) if columns else 1
    if num_cols == 1:
        # Single column — no wrapper needed
        col_sections = columns.get(1, [])
        content = "\n".join(html for _, _, html in col_sections)
    else:
        # Multi-column layout
        col_divs = []
        col_widths = []
        for col_num in range(1, num_cols + 1):
            col_sections = columns.get(col_num, [])
            has_list = any(k in list_sections for _, k, _ in col_sections)
            col_widths.append("auto" if has_list else "1fr")
            inner = "\n".join(html for _, _, html in col_sections)
            col_divs.append(f'<div class="page-col">{inner}</div>')
        grid_cols = " ".join(col_widths)
        content = (
            f'<div class="page-grid" style="grid-template-columns: {grid_cols};">'
            + "\n".join(col_divs)
            + '</div>'
        )

    return HTML_TEMPLATE.format(table_id=esc(table_id), content=content)


def find_table_dir(table_id):
    """Find table data directory — matches TABLE_ID or 'TABLE_ID opponent'."""
    exact = DATA_DIR / table_id
    if exact.exists():
        return exact
    matches = list(DATA_DIR.glob(f"{table_id} *"))
    if len(matches) == 1:
        return matches[0]
    return exact  # will fail later with "not found"


def main():
    if len(sys.argv) < 2:
        print("Usage: python -m bga_tracker.innovation.format_state TABLE_ID")
        sys.exit(1)

    table_id = sys.argv[1]
    table_dir = find_table_dir(table_id)

    if not table_dir.exists():
        print(f"ERROR: Table directory not found: {DATA_DIR / table_id}")
        sys.exit(1)

    state_json = table_dir / "game_state.json"
    if not state_json.exists():
        print(f"ERROR: File not found: {state_json}")
        sys.exit(1)

    with open(state_json) as f:
        state = json.load(f)

    # Rename folder to include opponent name
    _, opponent = find_players(state)
    new_dir = DATA_DIR / f"{table_id} {opponent}"
    if table_dir != new_dir:
        table_dir.rename(new_dir)
        table_dir = new_dir

    html = format_summary(state, table_id)

    summary_path = table_dir / "summary.html"
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Written: {summary_path}")


if __name__ == "__main__":
    main()

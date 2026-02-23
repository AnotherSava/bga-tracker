"""
Innovation Game State Summary Formatter

Reads game_state_player.json and produces summary.html showing
hidden information from both perspectives, with card images.

Usage: python scripts/innovation/format_state.py TABLE_ID

Input:  data/<TABLE_ID>/game_state_player.json + .env for PLAYER_NAME
Output: data/<TABLE_ID>/summary.html
"""

import json
import os
import re
import sys
from html import escape as esc
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
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

# Color letter → full name mapping
COLOR_LETTER = {"B": "blue", "R": "red", "G": "green", "Y": "yellow", "P": "purple"}

# Icon position mapping (from isotropic Rg = [0, 5, 4, 1, 2, 3])
# Top row:    icons[0]  icons[5]  icons[4]
# Bottom row: icons[1]  icons[2]  icons[3]
TOP_POSITIONS = [0, 5, 4]
BOT_POSITIONS = [1, 2, 3]

_CARD_RE = re.compile(r'^\[(\d+)([BRGPY])\] (.+)$')
_UNKNOWN_RE = re.compile(r'^\?(\d+)?$')  # "?" or "?6"
_DECK_RE = re.compile(r'^\(([BRGPY])(\*)?\) (.+)$')

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
    with open(DATA_DIR / "cardinfo.json") as f:
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


def render_unknown(age=None):
    """Render a single hidden card, same size as a regular base card."""
    display_age = age if age is not None else ""
    return (
        f'<div class="card card-base b-gray">'
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
            if entry == "?":
                cards_html.append(render_unknown())
            else:
                m = _DECK_RE.match(entry)
                if m:
                    color_letter, star, name = m.group(1), m.group(2), m.group(3)
                    cards_html.append(render_card(name, age, color_letter, star=bool(star), is_deck=True))
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


def format_all_cards(card_set):
    """Format all cards of a given set, grouped by age."""
    _load_cardinfo()
    cards_by_age = {}
    for card in _card_by_name.values():
        if card.get("set") != card_set:
            continue
        age = card["age"]
        cards_by_age.setdefault(age, []).append(card)

    rows = []
    for age in range(1, 11):
        cards = sorted(cards_by_age.get(age, []), key=lambda c: (COLOR_LETTER.get(c["color"][0].upper(), c["color"]), c["name"]))
        cards_html = []
        for card in cards:
            ci = card["color"][0].upper()
            # Reverse lookup color letter
            cl = {"blue": "B", "red": "R", "green": "G", "yellow": "Y", "purple": "P"}.get(card["color"], "B")
            cards_html.append(render_card(card["name"], age, cl))
        row_content = "".join(cards_html)
        rows.append(
            f'<div class="deck-age">'
            f'<span class="deck-age-label">{age}</span>'
            f'<div class="card-row">{row_content}</div>'
            f'</div>'
        )
    return "\n".join(rows)


def format_opponent_zone(entries):
    """Format opponent's hand or score as card divs, sorted by age (known before unknown)."""
    if not entries:
        return '<div class="hand-row"><span class="row-label"> </span><div class="card-row"><div class="empty-card">empty</div></div></div>'
    # Parse entries into (age, is_unknown, html) tuples for sorting
    parsed = []
    for entry in entries:
        um = _UNKNOWN_RE.match(entry)
        if um:
            age = int(um.group(1)) if um.group(1) else 0
            parsed.append((age, 1, render_unknown(age if age else None)))
        else:
            star = entry.endswith(" *")
            raw = entry[:-2] if star else entry
            m = _CARD_RE.match(raw)
            if m:
                age, color_letter, name = int(m.group(1)), m.group(2), m.group(3)
                parsed.append((age, 0, render_card(name, age, color_letter)))
            else:
                parsed.append((0, 1, render_unknown()))
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
        if entry.endswith(" *"):
            raw = entry[:-2]
            m = _CARD_RE.match(raw)
            if m:
                age, color_letter, name = m.group(1), m.group(2), m.group(3)
                revealed.append(render_card(name, int(age), color_letter, star=True))
            else:
                revealed.append(render_unknown())
        else:
            m = _CARD_RE.match(entry)
            if m:
                age, color_letter, name = m.group(1), m.group(2), m.group(3)
                hidden.append(render_card(name, int(age), color_letter))
            else:
                hidden.append(render_unknown())

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
        um = _UNKNOWN_RE.match(entry)
        if um:
            age = int(um.group(1)) if um.group(1) else None
            hidden.append(render_unknown(age))
            continue
        star = entry.endswith(" *")
        raw = entry[:-2] if star else entry
        m = _CARD_RE.match(raw)
        if not m:
            continue
        age, color_letter, name = m.group(1), m.group(2), m.group(3)
        card_html = render_card(name, int(age), color_letter, star=star)
        if star:
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

.section {{ margin-bottom: 12px; }}
.section-title {{ font-size: 13px; margin-bottom: 4px; font-weight: bold; }}
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
.toggle-btn {{ cursor: pointer; vertical-align: middle; }}
.toggle-btn svg {{ width: 16px; height: 16px; fill: #888; }}
.toggle-btn:hover svg {{ fill: #bbb; }}
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
function toggleDeck(btn, id) {{
  var deck = document.getElementById(id);
  var open = btn.getAttribute('data-open');
  var closed = btn.getAttribute('data-closed');
  if (deck.style.display === 'none') {{
    deck.style.display = '';
    btn.innerHTML = closed;
  }} else {{
    deck.style.display = 'none';
    btn.innerHTML = open;
  }}
}}
</script>
</body>
</html>"""


def format_summary(state, table_id):
    """Assemble the full summary as HTML."""
    me, opponent = find_players(state)

    sections = []
    eye_open_esc = esc(ICON_EYE_OPEN)
    eye_closed_esc = esc(ICON_EYE_CLOSED)

    # Opponent hand
    sections.append(
        f'<div class="section">'
        f'<div class="section-title">Hand &mdash; opponent</div>'
        f'{format_opponent_zone(state.get("hand", {}).get(opponent, []))}'
        f'</div>'
    )

    # My hand
    sections.append(
        f'<div class="section">'
        f'<div class="section-title">Hand &mdash; me</div>'
        f'{format_my_hand(state.get("hand", {}).get(me, []))}'
        f'</div>'
    )

    # Opponent score
    opp_score = state.get("score", {}).get(opponent, [])
    if opp_score:
        sections.append(
            f'<div class="section">'
            f'<div class="section-title">Score &mdash; opponent</div>'
            f'{format_opponent_zone(opp_score)}'
            f'</div>'
        )

    # My score
    my_score = state.get("score", {}).get(me, [])
    if my_score:
        sections.append(
            f'<div class="section">'
            f'<div class="section-title">Score &mdash; me</div>'
            f'{format_my_zone(my_score)}'
            f'</div>'
        )

    # DECK (base)
    sections.append(
        f'<div class="section">'
        f'<div class="section-title">Base deck <span class="toggle-btn" data-open="{eye_open_esc}" data-closed="{eye_closed_esc}" onclick="toggleDeck(this, \'base-deck\')">{ICON_EYE_CLOSED}</span></div>'
        f'<div id="base-deck">{format_deck_section(state.get("actual_deck", {}))}</div>'
        f'</div>'
    )

    # Cities deck
    sections.append(
        f'<div class="section">'
        f'<div class="section-title">Cities deck <span class="toggle-btn" data-open="{eye_open_esc}" data-closed="{eye_closed_esc}" onclick="toggleDeck(this, \'cities-deck\')">{ICON_EYE_OPEN}</span></div>'
        f'<div id="cities-deck" style="display:none">{format_cities_section(state.get("actual_deck", {}))}</div>'
        f'</div>'
    )

    # Base list (all base cards)
    sections.append(
        f'<div class="section">'
        f'<div class="section-title">Base list <span class="toggle-btn" data-open="{eye_open_esc}" data-closed="{eye_closed_esc}" onclick="toggleDeck(this, \'base-list\')">{ICON_EYE_OPEN}</span></div>'
        f'<div id="base-list" style="display:none">{format_all_cards(0)}</div>'
        f'</div>'
    )

    # Cities list (all cities cards)
    sections.append(
        f'<div class="section">'
        f'<div class="section-title">Cities list <span class="toggle-btn" data-open="{eye_open_esc}" data-closed="{eye_closed_esc}" onclick="toggleDeck(this, \'cities-list\')">{ICON_EYE_OPEN}</span></div>'
        f'<div id="cities-list" style="display:none">{format_all_cards(3)}</div>'
        f'</div>'
    )

    content = "\n".join(sections)
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
        print("Usage: python scripts/innovation/format_state.py TABLE_ID")
        sys.exit(1)

    table_id = sys.argv[1]
    table_dir = find_table_dir(table_id)

    if not table_dir.exists():
        print(f"ERROR: Table directory not found: {DATA_DIR / table_id}")
        sys.exit(1)

    player_json = table_dir / "game_state_player.json"
    if not player_json.exists():
        print(f"ERROR: File not found: {player_json}")
        sys.exit(1)

    with open(player_json) as f:
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

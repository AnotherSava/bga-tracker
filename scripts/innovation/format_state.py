"""
Innovation Game State Summary Formatter

Reads game_state_player.json and produces summary.html showing
hidden information from both perspectives.

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

COLOR_CSS = {
    "B": "#4a9eff",
    "R": "#ff4444",
    "G": "#44bb44",
    "Y": "#ccaa00",
    "P": "#bb66ff",
}

_CARD_RE = re.compile(r'^\[(\d+)([BRGPY])\] (.+)$')
_DECK_RE = re.compile(r'^\(([BRGPY])(\*)?\) (.+)$')


def colorize_card(entry):
    """Convert '[6G] Name' to colored HTML. Returns (html, plain_text).
    Drops the color letter: [6G] Name -> [6] Name in green."""
    m = _CARD_RE.match(entry)
    if not m:
        return esc(entry), entry
    age, color, name = m.group(1), m.group(2), m.group(3)
    css = COLOR_CSS.get(color, "#d4d4d4")
    plain = f"[{age}] {name}"
    html = f'<span style="color:{css}">[{age}] {esc(name)}</span>'
    return html, plain


def colorize_deck(entry):
    """Convert '(C) Name' or '(C*) Name' to colored HTML. Returns (html, plain_text).
    Drops the prefix: (R) Name -> Name in red, (R*) Name -> Name* in red."""
    m = _DECK_RE.match(entry)
    if not m:
        return esc(entry), entry
    color, star, name = m.group(1), m.group(2), m.group(3)
    css = COLOR_CSS.get(color, "#d4d4d4")
    star_str = "*" if star else ""
    plain = f"{name}{star_str}"
    html = f'<span style="color:{css}">{esc(name)}</span>{star_str}'
    return html, plain


def dim(text):
    return f'<span style="color:#666">{esc(text)}</span>'


def bold(text):
    return f'<b>{esc(text)}</b>'


def find_players(state):
    """Derive my player and opponent from state board keys + PERSPECTIVE."""
    players = list(state["board"].keys())
    if PERSPECTIVE not in players:
        print(f"ERROR: PLAYER_NAME '{PERSPECTIVE}' not found in board players: {players}")
        sys.exit(1)
    opponent = [p for p in players if p != PERSPECTIVE][0]
    return PERSPECTIVE, opponent


def format_deck_section(actual_deck):
    """Format DECK (base only) section as HTML lines."""
    lines = []
    for age in range(1, 11):
        age_str = str(age)
        base = actual_deck.get(age_str, {}).get("base", [])
        if not base:
            lines.append(f"{age:2d}:")
            continue
        parts = []
        i = 0
        while i < len(base):
            if base[i] == "?":
                count = 0
                while i < len(base) and base[i] == "?":
                    count += 1
                    i += 1
                parts.append(dim(f"? x {count}") if count > 1 else dim("?"))
            else:
                html, _ = colorize_deck(base[i])
                parts.append(html)
                i += 1
        lines.append(f"{age:2d}:  {' | '.join(parts)}")
    return lines


def format_opponent_zone(entries):
    """Format opponent's hand or score as HTML."""
    if not entries:
        return dim("(empty)")
    parts = []
    unknown_count = 0
    for entry in entries:
        if entry == "?":
            unknown_count += 1
        else:
            if entry.endswith(" *"):
                entry = entry[:-2]
            html, _ = colorize_card(entry)
            parts.append(html)
    if unknown_count > 0:
        parts.append(dim(f"? x {unknown_count}") if unknown_count > 1 else dim("?"))
    return " | ".join(parts) if parts else dim("(empty)")


def format_my_zone(entries):
    """Format my score (known to opponent) as HTML."""
    if not entries:
        return dim("(empty)")
    parts = []
    unknown_count = 0
    for entry in entries:
        if entry.endswith(" *"):
            html, _ = colorize_card(entry[:-2])
            parts.append(html)
        else:
            unknown_count += 1
    if unknown_count > 0:
        parts.append(dim(f"? x {unknown_count}") if unknown_count > 1 else dim("?"))
    return " | ".join(parts) if parts else dim("(empty)")


def format_my_hand(entries):
    """Format my hand as two HTML columns: known (left) and hidden (right)."""
    if not entries:
        return dim("(empty)")
    known = []   # list of (html, plain)
    hidden = []
    for entry in entries:
        if entry == "?":
            continue
        if entry.endswith(" *"):
            known.append(colorize_card(entry[:-2]))
        else:
            hidden.append(colorize_card(entry))
    if not known and not hidden:
        return dim("(empty)")

    left_header = "known"
    right_header = "hidden"
    gap = "    "

    left_width = max(
        len(left_header),
        max((len(plain) for _, plain in known), default=0),
    )

    lines = []
    if hidden:
        lines.append(f'  <span style="color:#888">{left_header:<{left_width}}{gap}{right_header}</span>')
    else:
        lines.append(f'  <span style="color:#888">{left_header}</span>')

    max_rows = max(len(known), len(hidden))
    for i in range(max_rows):
        if i < len(known):
            l_html, l_plain = known[i]
            l_pad = " " * (left_width - len(l_plain))
        else:
            l_html, l_pad = "", " " * left_width

        if i < len(hidden):
            r_html, _ = hidden[i]
        else:
            r_html = ""

        if r_html:
            lines.append(f"  {l_html}{l_pad}{gap}{r_html}")
        elif l_html:
            lines.append(f"  {l_html}")

    return "\n".join(lines)


HTML_TEMPLATE = """\
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Innovation &mdash; {table_id}</title>
<style>
body {{ background: #1e1e1e; color: #d4d4d4; font-family: Consolas, 'Courier New', monospace;
       font-size: 14px; padding: 20px; }}
pre  {{ line-height: 1.4; }}
</style>
</head>
<body>
<pre>{content}</pre>
</body>
</html>"""


def format_summary(state, table_id):
    """Assemble the full summary as HTML."""
    me, opponent = find_players(state)

    sections = []

    # DECK (base)
    sections.append(bold("=== DECK (base) ==="))
    sections.extend(format_deck_section(state.get("actual_deck", {})))

    # Opponent hand
    sections.append("")
    sections.append(bold(f"=== {opponent} hand ==="))
    sections.append(format_opponent_zone(state.get("hand", {}).get(opponent, [])))

    # My hand
    sections.append("")
    sections.append(bold("=== My hand ==="))
    sections.append(format_my_hand(state.get("hand", {}).get(me, [])))

    # Opponent score
    sections.append("")
    sections.append(bold(f"=== {opponent} score ==="))
    sections.append(format_opponent_zone(state.get("score", {}).get(opponent, [])))

    # My score (known to opponent)
    sections.append("")
    sections.append(bold(f"=== My score (known to {opponent}) ==="))
    sections.append(format_my_zone(state.get("score", {}).get(me, [])))

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

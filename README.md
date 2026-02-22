# BGA Tracker

Board games have a lot of information that is technically public but hard to track mentally. In turn-based games on [Board Game Arena](https://boardgamearena.com) this is even worse — hours or days pass between turns, and whatever you noticed earlier is long forgotten. Recovering it means scrolling through pages of game logs. This project does it for you and presents a brief, readable summary.

My initial focus is on 2p games of **Innovation** with Cities of Destiny expansion. No more struggling to remember:
- deck stack order after consecutive Alchemy or Physics calls, or returning cards after playing a city
- cards kept in the opponent's hand after melding a particular city
- cards revealed with Oars


> **Note:** Only tested on Windows. Scripts, paths, and commands all assume a Windows environment.

## Setup

```
python -m venv venv
venv/Scripts/pip install -r requirements.txt
venv/Scripts/playwright install chromium
```

Create a `.env` file in the project root:
```
PLAYER_NAME=YourBGAUsername
```

## How it works

1. A Playwright-controlled browser navigates to the BGA game page and fetches the full notification history via the BGA API
2. A JS script (running in the browser context) extracts card transfer events into a structured game log
3. A Python script replays every card movement from the log, tracking current locations, deck stack order, and which cards the opponent knows about
4. A formatter produces a colored HTML summary of the current game state from both perspectives

Player names are detected automatically from the game log. The `PLAYER_NAME` in `.env` determines which side is "me" vs "opponent".

## Usage

### 1. Start the browser helper

```
venv/Scripts/python scripts/browse.py
```

This opens a persistent Chrome session. Commands are sent by writing to `scripts/cmd.txt`; results appear in `output/result.txt`.

### 2. Extract game log

Send these commands (one at a time, waiting for each result):
```
goto https://boardgamearena.com/<N>/innovation/innovation?table=TABLE_ID
eval scripts/fetch_full_history.js
eval scripts/innovation/extract_log.js
```

Save the final output to `data/<TABLE_ID>/game_log.json`.

### 3. Track card state

```
venv/Scripts/python scripts/innovation/track_state.py TABLE_ID
```

Produces `game_state.json` (full structured state) and `game_state_player.json` (human-readable player view).

### 4. Format summary

```
venv/Scripts/python scripts/innovation/format_state.py TABLE_ID
```

Produces `summary.html` — a colored HTML page showing deck contents, hands, and scores from both perspectives. Open it in a browser.

On first run, renames the data folder to include the opponent name (e.g. `809765534 jamdalla`). Subsequent runs find the renamed folder automatically.

## File structure

```
scripts/
  browse.py                     — Playwright-based browser helper
  fetch_full_history.js         — BGA notification history fetch (generic, any game)
  innovation/
    extract_log.js              — notification parser (browser)
    track_state.py              — card state tracker
    format_state.py             — HTML summary formatter
data/
  cardinfo.json                 — shared card database (sets 0 + 3, 210 cards)
  <TABLE_ID> <opponent>/        — per-game data
    game_log.json                — extracted game log (input)
    game_state.json              — full structured state (output)
    game_state_player.json       — human-readable player view (output)
    summary.html                 — colored HTML summary (output)
.env                            — player name config (not committed)
```

## Output format

### game_state.json

Cards grouped by location with full metadata:

```json
{
  "deck": { "base": [...], "cities": [...] },
  "deck_stacks": {
    "1": { "base": [null, ...], "cities": [null, ...], "achievement": null }
  },
  "board": { "Player1": [...] },
  "hand":  { "Player1": [...] },
  "score": { "Player1": [...] }
}
```

- Each card: `{name, age, color, set}`. Hand/score cards also have `known: true/false`.
- `deck_stacks`: ordered draw piles per (age, set). Index 0 = top. `null` = unknown, `"Card Name"` = known (from a visible return). `achievement`: `null` = unknown card removed, `false` = no achievement (age 10).

### game_state_player.json

```json
{
  "actual_deck": {
    "1": { "base": ["?", "?"], "cities": ["?", "?", "?"] },
    "6": { "base": ["?", "(G*) Sailing"], "cities": ["?"] }
  },
  "deck": ["[6B] Astronomy", ...],
  "board": { "Player1": ["[1B] Clothing", ...] },
  "hand":  { "Player1": ["[3R] Optics *", ...] },
  "score": { "Player1": [...] }
}
```

- `actual_deck`: draw piles grouped by age. `"?"` = unknown, `"(C) Name"` = known card, `"(C*) Name"` = known to both players. Only ages with cards remaining.
- Color initials: B=blue, R=red, G=green, Y=yellow, P=purple.
- `*` = card known to opponent.

### summary.html

![summary.html example](screenshots/summary.png)

Colored HTML page (dark theme, monospace) with five sections:
- **DECK (base)** — draw pile by age, known cards colored by Innovation color
- **Opponent hand** — named cards shown, unknowns grouped as `? x N`
- **My hand** — two-column layout: known to opponent vs hidden
- **Opponent score** — same format as opponent hand
- **My score** — known to opponent vs hidden count

## Innovation-specific notes

### Deck stack tracking

Separate draw piles per (age, set). Cards drawn from top, returned to bottom.

Initialization from `cardinfo.json`:
- Base ages 1-9: card count minus 1 (achievement removed)
- Base age 1: additionally minus 2 per player (initial deal, not logged)
- Base age 10: full count
- Cities all ages: full count

### Set identification

`extract_log.js` extracts the BGA `type` field from spectator notifications:
- BGA type `0` = base (set 0 in cardinfo.json)
- BGA type `2` = cities (set 3 in cardinfo.json)

Hidden transfers include "from base" or "from cities" suffix in the extracted log.

### Known flag

A card is marked `known` (visible to opponent) when:
1. Drawn and revealed publicly
2. Transferred between players
3. Was ever on a board (board cards are public)
4. Part of a "reveals his hand" event

The flag is sticky — once set, it stays true regardless of further movements.

### Name resolution

BGA lowercases some words in card names (e.g. "The wheel" vs "The Wheel"). The tracker uses case-insensitive lookup.

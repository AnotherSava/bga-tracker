"""
Innovation Card State Tracker

Reads game_log.json (extracted from BGA), processes all card movements,
and outputs the current location of every card.

Usage: python track_state.py TABLE_ID

Input:  data/cardinfo.json, data/<TABLE_ID>/game_log.json
Output: data/<TABLE_ID>/game_state.json, data/<TABLE_ID>/game_state_player.json
"""

import json
import os
import re
import sys
from pathlib import Path
from collections import defaultdict

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
CARDINFO_PATH = DATA_DIR / "cardinfo.json"

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

COLOR_ORDER = {"blue": 0, "red": 1, "green": 2, "yellow": 3, "purple": 4}
COLOR_INITIAL = {"blue": "B", "red": "R", "green": "G", "yellow": "Y", "purple": "P"}
SET_LABEL = {0: "base", 3: "cities"}
LABEL_TO_SET = {"base": 0, "cities": 3}


def load_card_database():
    """Load card info from cardinfo.json. Returns dict keyed by card name.
    Also returns a lowercase->canonical name mapping for fuzzy lookup."""
    with open(CARDINFO_PATH) as f:
        raw = json.load(f)

    cards = {}
    # BGA game uses base (set 0) + Cities of Destiny (set 3)
    for item in raw:
        if item is None:
            continue
        if "age" not in item or "color" not in item:
            continue  # skip achievements and other non-card entries
        s = item.get("set")
        if s not in (0, 3):
            continue  # only base + cities of destiny
        cards[item["name"]] = {
            "name": item["name"],
            "age": item["age"],
            "color": item["color"],
            "set": s,
        }

    # Build case-insensitive lookup (BGA lowercases some words in multi-word names)
    name_lookup = {}
    for name in cards:
        name_lookup[name.lower()] = name

    return cards, name_lookup


def sort_cards(card_list):
    """Sort cards by age, then color order, then name."""
    return sorted(card_list, key=lambda c: (c["age"], COLOR_ORDER.get(c["color"], 99), c["name"]))


def extract_players(log_data):
    """Extract player names from log entries.
    Looks for 'PLAYER chooses a card.' messages at the start of the game."""
    players = []
    choose_re = re.compile(r"^(.+?) chooses a card\.$")
    for entry in log_data["log"]:
        m = choose_re.match(entry["msg"])
        if m:
            name = m.group(1)
            if name not in players:
                players.append(name)
        if len(players) >= 2:
            break
    if not players:
        # Fallback: extract from first meld messages
        meld_re = re.compile(r"^(.+?) melds \[")
        for entry in log_data["log"]:
            m = meld_re.match(entry["msg"])
            if m:
                name = m.group(1)
                if name not in players:
                    players.append(name)
            if len(players) >= 2:
                break
    return players


def build_player_pattern(players):
    """Build regex alternation for player names."""
    return "|".join(re.escape(p) for p in players)


def resolve_name(raw_name, card_db, name_lookup):
    """Resolve a card name from the log to its canonical DB name."""
    if raw_name in card_db:
        return raw_name
    lower = raw_name.lower()
    if lower in name_lookup:
        return name_lookup[lower]
    return None


def init_deck_stacks(card_db, num_players):
    """Initialize deck stacks from card database.
    Returns dict keyed by (age, set) -> list (index 0 = top).
    Each entry is None (unknown card).

    Set 0 ages 1-9: count - 1 (one unknown card removed as achievement)
    Set 0 age 10: full count (no achievement)
    Set 3 all ages: full count (no achievements from cities)

    Additionally subtracts the initial deal: each player draws 2 base age 1
    cards at game start (not logged as transfer notifications).
    """
    counts = defaultdict(int)
    for card in card_db.values():
        counts[(card["age"], card["set"])] += 1

    initial_deal = num_players * 2  # 2 base age 1 cards per player

    stacks = {}
    for (age, card_set), count in sorted(counts.items()):
        n = count
        if card_set == 0 and 1 <= age <= 9:
            n -= 1  # achievement card removed
        if card_set == 0 and age == 1:
            n -= initial_deal  # initial deal (unlogged)
        stacks[(age, card_set)] = [None] * n

    return stacks


def parse_log(card_db, name_lookup, game_log_path):
    """
    Parse game_log.json and track card locations and deck stack order.
    Returns (players, state, known_set, deck_stacks) where:
      players: list of player names extracted from the log
      state: dict card_name -> location string
      known_set: set of card names known to opponent
      deck_stacks: dict (age, set) -> ordered list (index 0 = top),
                   entries are card_name (str) or None (unknown)
    """
    with open(game_log_path) as f:
        log_data = json.load(f)

    players = extract_players(log_data)
    if not players:
        print("ERROR: Could not extract player names from log")
        sys.exit(1)
    print(f"Players: {', '.join(players)}")

    PP = build_player_pattern(players)

    # Initialize all cards in deck
    state = {}
    for name in card_db:
        state[name] = "deck"

    # Initialize deck stacks
    deck_stacks = init_deck_stacks(card_db, len(players))

    # Cards known to the opponent (from PERSPECTIVE's view)
    known = set()

    # Cards that have been on a board at any point (public knowledge)
    was_on_board = set()

    # Count of unidentified cards in each player's hand, keyed by (age, card_set)
    # Starts with two age-1 base cards per player: initial deal (unlogged)
    unknown_hand = {p: defaultdict(int) for p in players}
    for p in players:
        unknown_hand[p][(1, 0)] = 2

    # Count of unidentified cards in each player's score pile, keyed by (age, card_set)
    unknown_score = {p: defaultdict(int) for p in players}

    # --- Transfer patterns (with named cards) ---
    # Order matters: more specific patterns first
    patterns = [
        # P melds [A] CARD from hand.
        (re.compile(rf"^({PP}) melds \[(\d+)\] (.+?) from hand\.$"),
         lambda m: ("hand:" + m.group(1), "board:" + m.group(1), m.group(3))),

        # P tucks [A] CARD from hand.
        (re.compile(rf"^({PP}) tucks \[(\d+)\] (.+?) from hand\.$"),
         lambda m: ("hand:" + m.group(1), "board:" + m.group(1), m.group(3))),

        # P draws and reveals [A] CARD.
        (re.compile(rf"^({PP}) draws and reveals \[(\d+)\] (.+?)\.$"),
         lambda m: ("deck", "hand:" + m.group(1), m.group(3))),

        # P places [A] CARD in hand. (skip — redundant after draws and reveals)
        (re.compile(rf"^({PP}) places \[(\d+)\] (.+?) in hand\.$"),
         lambda m: (None, None, m.group(3))),  # skip

        # P draws [A] CARD.
        (re.compile(rf"^({PP}) draws \[(\d+)\] (.+?)\.$"),
         lambda m: ("deck", "hand:" + m.group(1), m.group(3))),

        # P melds [A] CARD. (no "from hand" — e.g. after draw+reveal via Mysticism)
        (re.compile(rf"^({PP}) melds \[(\d+)\] (.+?)\.$"),
         lambda m: (None, "board:" + m.group(1), m.group(3))),

        # P scores [A] CARD from hand.
        (re.compile(rf"^({PP}) scores \[(\d+)\] (.+?) from hand\.$"),
         lambda m: ("hand:" + m.group(1), "score:" + m.group(1), m.group(3))),

        # P scores [A] CARD from board.
        (re.compile(rf"^({PP}) scores \[(\d+)\] (.+?) from board\.$"),
         lambda m: ("board:" + m.group(1), "score:" + m.group(1), m.group(3))),

        # P1 transfers [A] CARD from hand to P2's hand.
        (re.compile(rf"^({PP}) transfers \[(\d+)\] (.+?) from hand to ({PP})'s hand\.$"),
         lambda m: ("hand:" + m.group(1), "hand:" + m.group(4), m.group(3))),

        # P1 transfers [A] CARD from hand to P2's score pile.
        (re.compile(rf"^({PP}) transfers \[(\d+)\] (.+?) from hand to ({PP})'s score pile\.$"),
         lambda m: ("hand:" + m.group(1), "score:" + m.group(4), m.group(3))),

        # P returns [A] CARD from hand.
        (re.compile(rf"^({PP}) returns \[(\d+)\] (.+?) from hand\.$"),
         lambda m: ("hand:" + m.group(1), "deck", m.group(3))),

        # P returns [A] CARD from score pile.
        (re.compile(rf"^({PP}) returns \[(\d+)\] (.+?) from score pile\.$"),
         lambda m: ("score:" + m.group(1), "deck", m.group(3))),

        # P returns [A] CARD from board.
        (re.compile(rf"^({PP}) returns \[(\d+)\] (.+?) from board\.$"),
         lambda m: ("board:" + m.group(1), "deck", m.group(3))),

        # P returns [A] CARD from board to hand.
        (re.compile(rf"^({PP}) returns \[(\d+)\] (.+?) from board to hand\.$"),
         lambda m: ("board:" + m.group(1), "hand:" + m.group(1), m.group(3))),

        # P returns revealed [A] CARD.
        (re.compile(rf"^({PP}) returns revealed \[(\d+)\] (.+?)\.$"),
         lambda m: ("revealed", "deck", m.group(3))),

        # P draws and scores [A] CARD.
        (re.compile(rf"^({PP}) draws and scores \[(\d+)\] (.+?)\.$"),
         lambda m: ("deck", "score:" + m.group(1), m.group(3))),

        # P draws and melds [A] CARD.
        (re.compile(rf"^({PP}) draws and melds \[(\d+)\] (.+?)\.$"),
         lambda m: ("deck", "board:" + m.group(1), m.group(3))),

        # P moves [A] CARD from score pile to hand.
        (re.compile(rf"^({PP}) moves \[(\d+)\] (.+?) from score pile to hand\.$"),
         lambda m: ("score:" + m.group(1), "hand:" + m.group(1), m.group(3))),

        # P achieves [A] CARD.
        (re.compile(rf"^({PP}) achieves \[(\d+)\] (.+?)\.$"),
         lambda m: ("board:" + m.group(1), "achieved", m.group(3))),

        # P achieves CARD. (special achievements like "World" — not in card DB)
        (re.compile(rf"^({PP}) achieves (.+?)\.$"),
         lambda m: (None, None, None)),  # skip — special achievement, not a card transfer

        # P1 transfers [A] CARD from board to P2's board.
        (re.compile(rf"^({PP}) transfers \[(\d+)\] (.+?) from board to ({PP})'s board\.$"),
         lambda m: ("board:" + m.group(1), "board:" + m.group(4), m.group(3))),

        # P1 transfers [A] CARD from P2's board to board.
        (re.compile(rf"^({PP}) transfers \[(\d+)\] (.+?) from ({PP})'s board to board\.$"),
         lambda m: ("board:" + m.group(4), "board:" + m.group(1), m.group(3))),

        # P moves [A] CARD (board -> board). — Compass-style demand: P's board to other player's board
        (re.compile(rf"^({PP}) moves \[(\d+)\] (.+?) \(board -> board\)\.$"),
         lambda m: ("board:" + m.group(1),
                     "board:" + [p for p in players if p != m.group(1)][0],
                     m.group(3))),
    ]

    # Hidden patterns — no card name visible, has age + set info
    # "from base" = set 0, "from cities" = set 3
    # Action tuple: (deck_effect, state_from, state_to)
    #   deck_effect: "pop" (draw), "push" (return to deck), None
    #   state_from: "hand"/"board"/"score"/None (source location prefix)
    #   state_to: "deck"/"score"/None (destination)
    hidden_patterns = [
        # P draws a [N] from base/cities.
        (re.compile(rf"^({PP}) draws a \[(\d+)\] from (base|cities)\.$"),
         ("pop", None, None)),
        # P draws and scores a [N] from base/cities.
        (re.compile(rf"^({PP}) draws and scores a \[(\d+)\] from (base|cities)\.$"),
         ("pop", None, None)),
        # P returns a [N] from his hand from base/cities.
        (re.compile(rf"^({PP}) returns a \[(\d+)\] from his hand from (base|cities)\.$"),
         ("push", "hand", "deck")),
        # P returns a [N] from his board from base/cities.
        (re.compile(rf"^({PP}) returns a \[(\d+)\] from his board from (base|cities)\.$"),
         ("push", "board", "deck")),
        # P returns a [N] from his score pile from base/cities.
        (re.compile(rf"^({PP}) returns a \[(\d+)\] from his score pile from (base|cities)\.$"),
         ("push", "score", "deck")),
        # P scores a [N] from his hand from base/cities.
        (re.compile(rf"^({PP}) scores a \[(\d+)\] from his hand from (base|cities)\.$"),
         (None, "hand", "score")),
        # P scores a [N] from his board from base/cities.
        (re.compile(rf"^({PP}) scores a \[(\d+)\] from his board from (base|cities)\.$"),
         (None, "board", "score")),
        # P transfers a [N] ... from base/cities. — too complex without card names
        (re.compile(rf"^({PP}) transfers a \[(\d+)\] .+ from (base|cities)\.$"),
         (None, None, None)),
        # P achieves a [N] from base/cities. — no deck effect
        (re.compile(rf"^({PP}) achieves a \[(\d+)\] from (base|cities)\.$"),
         (None, None, None)),
        # P achieves [null] CARD. — named achievements, no deck effect
        (re.compile(rf"^({PP}) achieves \[null\] .+?\.$"),
         "skip_no_set"),
    ]

    # "reveals his hand" pattern for known tracking
    reveal_pattern = re.compile(
        rf"^({PP}) reveals his hand: (.+)\.$"
    )

    for entry in log_data["log"]:
        msg = entry["msg"]

        # --- Handle "reveals his hand" (logWithCardTooltips) ---
        if entry["type"] == "logWithCardTooltips":
            rm = reveal_pattern.match(msg)
            if rm:
                card_list_str = rm.group(2)
                for part in card_list_str.split(", "):
                    space_idx = part.index(" ")
                    card_name = part[space_idx + 1:]
                    canonical = resolve_name(card_name, card_db, name_lookup)
                    if canonical:
                        known.add(canonical)
            continue  # logWithCardTooltips are not transfer entries

        # Only process transfer entries
        if entry["type"] != "transfer":
            continue

        # Normalize message for named pattern matching:
        # 1. Strip " from base"/" from cities" suffix added by extract_log.js
        # 2. Normalize "his hand" → "hand", "his board" → "board", etc.
        # (Keep original msg for hidden patterns which expect the suffix)
        clean_msg = re.sub(r" from (base|cities)\.$", ".", msg)
        clean_msg = re.sub(r"\bhis (hand|board|score pile)\b", r"\1", clean_msg)

        # Check hidden patterns first (no card name) — use original msg
        hidden_matched = False
        for hp_regex, hp_action in hidden_patterns:
            hm = hp_regex.match(msg)
            if hm:
                hidden_matched = True
                if hp_action == "skip_no_set":
                    break

                deck_effect, state_from, state_to = hp_action
                player = hm.group(1)
                age = int(hm.group(2))
                set_label = hm.group(3)
                card_set = LABEL_TO_SET[set_label]
                key = (age, card_set)

                # Deck stack effect
                if deck_effect == "pop":
                    if key in deck_stacks and deck_stacks[key]:
                        deck_stacks[key].pop(0)
                    else:
                        print(f"WARNING: Drew from empty stack ({age}, {set_label}): {msg}")
                elif deck_effect == "push":
                    if key in deck_stacks:
                        deck_stacks[key].append(None)
                    else:
                        print(f"WARNING: Unknown stack ({age}, {set_label}): {msg}")

                # Hidden draw to hand or score: track unknown card count
                if deck_effect == "pop" and not state_from and not state_to:
                    if "draws and scores" in msg:
                        unknown_score[player][key] += 1
                    else:
                        unknown_hand[player][key] += 1

                # Card state tracking — find matching card and update
                if state_from and state_to:
                    from_loc = f"{state_from}:{player}"
                    to_loc = "deck" if state_to == "deck" else f"{state_to}:{player}"
                    candidates = [
                        name for name, loc in state.items()
                        if loc == from_loc
                        and card_db[name]["age"] == age
                        and card_db[name]["set"] == card_set
                    ]
                    if candidates:
                        state[candidates[0]] = to_loc
                    else:
                        # No named card found — adjust unknown counts
                        if state_from == "hand" and unknown_hand[player][key] > 0:
                            unknown_hand[player][key] -= 1
                            if state_to == "score":
                                unknown_score[player][key] += 1
                        elif state_from == "score" and unknown_score[player][key] > 0:
                            unknown_score[player][key] -= 1
                            if state_to == "hand":
                                unknown_hand[player][key] += 1

                break
        if hidden_matched:
            continue

        # Try matching named-card patterns (use clean_msg)
        matched = False
        for regex, extractor in patterns:
            m = regex.match(clean_msg)
            if m:
                from_loc, to_loc, raw_card_name = extractor(m)

                # Skip entries with no card name (special achievements etc.)
                if raw_card_name is None:
                    matched = True
                    break

                card_name = resolve_name(raw_card_name, card_db, name_lookup)
                if card_name is None:
                    print(f"WARNING: Unknown card '{raw_card_name}' in: {msg}")
                    matched = True
                    break

                # "places in hand" is a skip (redundant)
                if from_loc is None and to_loc is None:
                    matched = True
                    break

                # "melds [N] CARD." without from_loc — use current location as source
                if from_loc is None:
                    from_loc = state.get(card_name, "deck")

                # Reconcile unknown tracking: if a named card is FROM hand/score
                # but its tracked state doesn't match, it was an unknown card
                current_loc = state.get(card_name)
                if from_loc and current_loc != from_loc:
                    card_age = card_db[card_name]["age"]
                    card_cs = card_db[card_name]["set"]
                    key = (card_age, card_cs)
                    if from_loc.startswith("hand:"):
                        hand_player = from_loc.split(":", 1)[1]
                        if unknown_hand[hand_player][key] > 0:
                            unknown_hand[hand_player][key] -= 1
                    elif from_loc.startswith("score:"):
                        score_player = from_loc.split(":", 1)[1]
                        if unknown_score[score_player][key] > 0:
                            unknown_score[score_player][key] -= 1

                # Update state
                state[card_name] = to_loc

                # --- Deck stack tracking for named transfers ---
                card_info = card_db[card_name]
                stack_key = (card_info["age"], card_info["set"])

                if from_loc == "deck" and stack_key in deck_stacks:
                    # Card drawn from deck — remove from top
                    stack = deck_stacks[stack_key]
                    if stack:
                        stack.pop(0)
                    else:
                        print(f"WARNING: Drew '{card_name}' from empty stack {stack_key}: {msg}")

                if to_loc == "deck" and stack_key in deck_stacks:
                    # Card returned to deck — append named card to bottom
                    deck_stacks[stack_key].append(card_name)

                # Track board visibility
                if to_loc.startswith("board:"):
                    was_on_board.add(card_name)

                # Track known status
                # Revealed cards (draws and reveals)
                if "draws and reveals" in msg:
                    known.add(card_name)

                # Transferred between players — both see it
                if "transfers" in msg and any(
                    f"to {p}'s" in msg for p in players
                ):
                    known.add(card_name)

                matched = True
                break

        if not matched:
            print(f"WARNING: Unrecognized transfer pattern: {msg}")
            if clean_msg != msg:
                print(f"  (cleaned: {clean_msg})")

    # Mark all cards that were ever on a board as known
    known.update(was_on_board)

    return players, state, known, deck_stacks, unknown_hand, unknown_score


def build_output(card_db, state, known, deck_stacks, players):
    """Build the structured game_state.json output."""
    result = {
        "deck": {"base": [], "cities": []},
        "deck_stacks": {},
        "board": {p: [] for p in players},
        "hand": {p: [] for p in players},
        "score": {p: [] for p in players},
    }

    for name, loc in state.items():
        card = dict(card_db[name])  # copy

        if loc == "deck":
            key = "base" if card["set"] == 0 else "cities"  # set 0=base, 3=cities
            result["deck"][key].append(card)
        elif loc.startswith("board:"):
            player = loc.split(":", 1)[1]
            result["board"][player].append(card)
        elif loc.startswith("hand:"):
            player = loc.split(":", 1)[1]
            card["known"] = name in known
            result["hand"][player].append(card)
        elif loc.startswith("score:"):
            player = loc.split(":", 1)[1]
            card["known"] = name in known
            result["score"][player].append(card)

    # Sort all lists
    result["deck"]["base"] = sort_cards(result["deck"]["base"])
    result["deck"]["cities"] = sort_cards(result["deck"]["cities"])
    for p in players:
        result["board"][p] = sort_cards(result["board"][p])
        result["hand"][p] = sort_cards(result["hand"][p])
        result["score"][p] = sort_cards(result["score"][p])

    # Build deck_stacks output grouped by age
    for (age, card_set), stack in sorted(deck_stacks.items()):
        age_str = str(age)
        if age_str not in result["deck_stacks"]:
            result["deck_stacks"][age_str] = {
                "base": [],
                "cities": [],
                # null = unknown card removed as achievement, false = no achievement
                "achievement": None if 1 <= age <= 9 else False,
            }
        label = SET_LABEL[card_set]
        result["deck_stacks"][age_str][label] = stack  # list with None/card_name

    return result


def deduce_achievements(card_db, state, deck_stacks):
    """Deduce age achievements from remaining hidden base cards.

    For each age 1-9, one base card was removed as an achievement.
    If all base cards of that age except one are accounted for
    (non-deck state or named in deck stacks), the remaining one
    is the achievement.

    Returns dict: age (int) -> list of candidate card names.
    """
    # Collect named cards in deck stacks
    named_in_deck = set()
    for stack in deck_stacks.values():
        for entry in stack:
            if entry is not None:
                named_in_deck.add(entry)

    achievements = {}
    for age in range(1, 10):
        # Base cards of this age with unknown location
        hidden = [
            name for name, loc in state.items()
            if loc == "deck"
            and card_db[name]["age"] == age
            and card_db[name]["set"] == 0
            and name not in named_in_deck
        ]
        achievements[age] = hidden
    return achievements


def card_to_short(card, include_known=False):
    """Format card as short string like '[3R] Optics' or '[3R] Optics *'."""
    ci = COLOR_INITIAL.get(card["color"], "?")
    s = f"[{card['age']}{ci}] {card['name']}"
    if include_known and card.get("known"):
        s += " *"
    return s


def stack_entry_to_player(entry, card_db, known=None):
    """Format a deck stack entry for player output.
    None -> '?', card_name -> '(C) Name' where C is color initial.
    Known cards (visible to opponent) get '(C*) Name'."""
    if entry is None:
        return "?"
    card = card_db.get(entry)
    if card:
        ci = COLOR_INITIAL.get(card["color"], "?")
        star = "*" if known and entry in known else ""
        return f"({ci}{star}) {entry}"
    return entry


def build_player_output(full_state, card_db, players, unknown_hand=None, unknown_score=None, known=None, achievements=None):
    """Build human-readable player perspective output."""
    result = {
        "actual_deck": {},
        "deck": [],  # base only (backward compat)
        "board": {p: [] for p in players},
        "hand": {p: [] for p in players},
        "score": {p: [] for p in players},
        "achievements": [],
    }

    # Deck: base only (backward compat)
    result["deck"] = [card_to_short(c) for c in full_state["deck"]["base"]]

    for p in players:
        result["board"][p] = [card_to_short(c) for c in full_state["board"][p]]
        result["hand"][p] = [card_to_short(c, include_known=True) for c in full_state["hand"][p]]
        # Add unknown hand cards with ages (from hidden draws we can't identify)
        if unknown_hand and unknown_hand.get(p):
            for (age, cs), count in sorted(unknown_hand[p].items()):
                if count > 0:
                    suffix = 'b' if cs == 0 else 'c'
                    result["hand"][p] += [f"?{age}{suffix}"] * count
        result["score"][p] = [card_to_short(c, include_known=True) for c in full_state["score"][p]]
        if unknown_score and unknown_score.get(p):
            for (age, cs), count in sorted(unknown_score[p].items()):
                if count > 0:
                    suffix = 'b' if cs == 0 else 'c'
                    result["score"][p] += [f"?{age}{suffix}"] * count

    # Build actual_deck from deck_stacks — only ages with cards remaining
    for age_str, stacks in full_state["deck_stacks"].items():
        base = stacks.get("base", [])
        cities = stacks.get("cities", [])
        if not base and not cities:
            continue
        result["actual_deck"][age_str] = {
            "base": [stack_entry_to_player(e, card_db, known) for e in base],
            "cities": [stack_entry_to_player(e, card_db, known) for e in cities],
        }

    # Achievements (ages 1-9)
    if achievements:
        for age in range(1, 10):
            candidates = achievements.get(age, [])
            if len(candidates) == 1 and candidates[0] in card_db:
                result["achievements"].append(card_to_short(card_db[candidates[0]]))
            else:
                result["achievements"].append(f"?{age}")

    return result


def print_summary(full_state, deck_stacks, players, unknown_hand=None):
    """Print a summary of card counts."""
    deck_base = len(full_state["deck"]["base"])
    deck_cities = len(full_state["deck"]["cities"])
    total = deck_base + deck_cities

    for p in players:
        total += len(full_state["board"][p])
        total += len(full_state["hand"][p])
        total += len(full_state["score"][p])

    print(f"Deck: {deck_base} base + {deck_cities} cities = {deck_base + deck_cities}")
    for p in players:
        b = len(full_state["board"][p])
        h = len(full_state["hand"][p])
        uh = sum(unknown_hand[p].values()) if unknown_hand and unknown_hand.get(p) else 0
        s = len(full_state["score"][p])
        hand_str = str(h + uh) if uh == 0 else f"{h}+{uh}?"
        print(f"{p}: board={b}, hand={hand_str}, score={s}")
    print(f"Total cards tracked: {total}")

    # Deck stack summary
    total_stack = sum(len(s) for s in deck_stacks.values())
    named_in_stack = sum(1 for s in deck_stacks.values() for e in s if e is not None)
    print(f"Deck stacks: {total_stack} cards ({named_in_stack} known positions)")


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
        print("Usage: python track_state.py TABLE_ID")
        sys.exit(1)

    table_id = sys.argv[1]
    table_dir = find_table_dir(table_id)

    if not table_dir.exists():
        print(f"ERROR: Table directory not found: {DATA_DIR / table_id}")
        sys.exit(1)

    game_log_path = table_dir / "game_log.json"
    state_out = table_dir / "game_state.json"
    player_out = table_dir / "game_state_player.json"

    card_db, name_lookup = load_card_database()
    print(f"Loaded {len(card_db)} cards from database (sets 0+3)")

    players, state, known, deck_stacks, unknown_hand, unknown_score = parse_log(card_db, name_lookup, game_log_path)
    print(f"Known cards (to opponent): {len(known)}")

    achievements = deduce_achievements(card_db, state, deck_stacks)
    deduced = sum(1 for v in achievements.values() if len(v) == 1)
    print(f"Achievements deduced: {deduced}/9")

    full_state = build_output(card_db, state, known, deck_stacks, players)
    print_summary(full_state, deck_stacks, players, unknown_hand)

    with open(state_out, "w") as f:
        json.dump(full_state, f, indent=2)
    print(f"Written: {state_out}")

    player_state = build_player_output(full_state, card_db, players, unknown_hand, unknown_score, known, achievements)
    with open(player_out, "w") as f:
        json.dump(player_state, f, indent=2)
    print(f"Written: {player_out}")


if __name__ == "__main__":
    main()

"""StateTracker: log parsing and regex patterns for Innovation game state."""

import json
import re
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from scripts.innovation.card import CardDB, LABEL_TO_SET
from scripts.innovation.game_state import GameState, Action


class StateTracker:
    """Processes an Innovation game log and builds a GameState."""

    def __init__(self, card_db, players, perspective):
        self.card_db = card_db
        self.players = players
        self.perspective = perspective
        self.game_state = GameState(card_db, players, perspective)

        self._pp = self._build_player_pattern()
        self._named_patterns = self._build_named_patterns()
        self._hidden_patterns = self._build_hidden_patterns()
        self._reveal_pattern = re.compile(
            rf"^({self._pp}) reveals his hand: (.+)\.$"
        )

    def _build_player_pattern(self):
        return "|".join(re.escape(p) for p in self.players)

    def initialize(self):
        """Set up initial game state."""
        self.game_state.init_game(len(self.players))

    def process_log(self, game_log_path):
        """Read game log JSON and process all entries."""
        with open(game_log_path) as f:
            log_data = json.load(f)

        for entry in log_data["log"]:
            self._process_entry(entry)

    def _process_entry(self, entry):
        """Process a single log entry."""
        msg = entry["msg"]

        # --- Handle "reveals his hand" (logWithCardTooltips) ---
        if entry["type"] == "logWithCardTooltips":
            rm = self._reveal_pattern.match(msg)
            if rm:
                player = rm.group(1)
                card_list_str = rm.group(2)
                card_names = []
                for part in card_list_str.split(", "):
                    space_idx = part.index(" ")
                    card_name = part[space_idx + 1:].lower()
                    card_names.append(card_name)
                self.game_state.reveal_hand(player, card_names)
            return  # logWithCardTooltips are not transfer entries

        # Only process transfer entries
        if entry["type"] != "transfer":
            return

        # Normalize message for named pattern matching
        clean_msg = re.sub(r" from (base|cities)\.$", ".", msg)
        clean_msg = re.sub(r"\bhis (hand|board|score pile)\b", r"\1", clean_msg)

        # Check hidden patterns first (use original msg)
        for hp_regex, hp_handler in self._hidden_patterns:
            hm = hp_regex.match(msg)
            if hm:
                action = hp_handler(hm)
                if action is not None:
                    self.game_state.move(action)
                return

        # Try named-card patterns (use clean_msg)
        for regex, extractor in self._named_patterns:
            m = regex.match(clean_msg)
            if m:
                action = extractor(m)
                if action is not None:
                    self.game_state.move(action)
                return

        raise ValueError(f"Unrecognized transfer pattern: {msg}")

    def get_result(self):
        """Return game state as JSON-serializable dict."""
        return self.game_state.to_json()

    # ------------------------------------------------------------------
    # Pattern builders
    # ------------------------------------------------------------------

    def _build_named_patterns(self):
        """Build regex patterns for named card transfers.

        Each entry: (compiled regex, extractor function returning Action or None).
        Order matters: more specific patterns before general ones.
        """
        PP = self._pp
        players = self.players

        return [
            # P melds [A] CARD from hand.
            (re.compile(rf"^({PP}) melds \[(\d+)\] (.+?) from hand\.$"),
             lambda m: Action(
                 source="hand", dest="board",
                 card_index=m.group(3).lower(),
                 source_player=m.group(1), dest_player=m.group(1))),

            # P tucks [A] CARD from hand.
            (re.compile(rf"^({PP}) tucks \[(\d+)\] (.+?) from hand\.$"),
             lambda m: Action(
                 source="hand", dest="board",
                 card_index=m.group(3).lower(),
                 source_player=m.group(1), dest_player=m.group(1))),

            # P draws and reveals [A] CARD.
            (re.compile(rf"^({PP}) draws and reveals \[(\d+)\] (.+?)\.$"),
             lambda m: Action(
                 source="deck", dest="revealed",
                 card_index=m.group(3).lower(),
                 dest_player=m.group(1), reveal=True)),

            # P places [A] CARD in hand. (from revealed zone after draw-and-reveal)
            (re.compile(rf"^({PP}) places \[(\d+)\] (.+?) in hand\.$"),
             lambda m: Action(
                 source="revealed", dest="hand",
                 card_index=m.group(3).lower(),
                 source_player=m.group(1), dest_player=m.group(1))),

            # P draws [A] CARD.
            (re.compile(rf"^({PP}) draws \[(\d+)\] (.+?)\.$"),
             lambda m: Action(
                 source="deck", dest="hand",
                 card_index=m.group(3).lower(),
                 dest_player=m.group(1))),

            # P melds [A] CARD. (from revealed zone, not hand)
            (re.compile(rf"^({PP}) melds \[(\d+)\] (.+?)\.$"),
             lambda m: Action(
                 source="revealed", dest="board",
                 card_index=m.group(3).lower(),
                 source_player=m.group(1), dest_player=m.group(1))),

            # P scores [A] CARD from hand.
            (re.compile(rf"^({PP}) scores \[(\d+)\] (.+?) from hand\.$"),
             lambda m: Action(
                 source="hand", dest="score",
                 card_index=m.group(3).lower(),
                 source_player=m.group(1), dest_player=m.group(1))),

            # P scores [A] CARD from board.
            (re.compile(rf"^({PP}) scores \[(\d+)\] (.+?) from board\.$"),
             lambda m: Action(
                 source="board", dest="score",
                 card_index=m.group(3).lower(),
                 source_player=m.group(1), dest_player=m.group(1))),

            # P1 transfers [A] CARD from hand to P2's hand.
            (re.compile(rf"^({PP}) transfers \[(\d+)\] (.+?) from hand to ({PP})'s hand\.$"),
             lambda m: Action(
                 source="hand", dest="hand",
                 card_index=m.group(3).lower(),
                 source_player=m.group(1), dest_player=m.group(4))),

            # P1 transfers [A] CARD from hand to P2's score pile.
            (re.compile(rf"^({PP}) transfers \[(\d+)\] (.+?) from hand to ({PP})'s score pile\.$"),
             lambda m: Action(
                 source="hand", dest="score",
                 card_index=m.group(3).lower(),
                 source_player=m.group(1), dest_player=m.group(4))),

            # P returns [A] CARD from hand.
            (re.compile(rf"^({PP}) returns \[(\d+)\] (.+?) from hand\.$"),
             lambda m: Action(
                 source="hand", dest="deck",
                 card_index=m.group(3).lower(),
                 source_player=m.group(1))),

            # P returns [A] CARD from score pile.
            (re.compile(rf"^({PP}) returns \[(\d+)\] (.+?) from score pile\.$"),
             lambda m: Action(
                 source="score", dest="deck",
                 card_index=m.group(3).lower(),
                 source_player=m.group(1))),

            # P returns [A] CARD from board.
            (re.compile(rf"^({PP}) returns \[(\d+)\] (.+?) from board\.$"),
             lambda m: Action(
                 source="board", dest="deck",
                 card_index=m.group(3).lower(),
                 source_player=m.group(1))),

            # P returns [A] CARD from board to hand.
            (re.compile(rf"^({PP}) returns \[(\d+)\] (.+?) from board to hand\.$"),
             lambda m: Action(
                 source="board", dest="hand",
                 card_index=m.group(3).lower(),
                 source_player=m.group(1), dest_player=m.group(1))),

            # P returns revealed [A] CARD.
            (re.compile(rf"^({PP}) returns revealed \[(\d+)\] (.+?)\.$"),
             lambda m: Action(
                 source="revealed", dest="deck",
                 card_index=m.group(3).lower(),
                 source_player=m.group(1))),

            # P draws and scores [A] CARD.
            (re.compile(rf"^({PP}) draws and scores \[(\d+)\] (.+?)\.$"),
             lambda m: Action(
                 source="deck", dest="score",
                 card_index=m.group(3).lower(),
                 dest_player=m.group(1))),

            # P draws and melds [A] CARD.
            (re.compile(rf"^({PP}) draws and melds \[(\d+)\] (.+?)\.$"),
             lambda m: Action(
                 source="deck", dest="board",
                 card_index=m.group(3).lower(),
                 dest_player=m.group(1))),

            # P moves [A] CARD from score pile to hand.
            (re.compile(rf"^({PP}) moves \[(\d+)\] (.+?) from score pile to hand\.$"),
             lambda m: Action(
                 source="score", dest="hand",
                 card_index=m.group(3).lower(),
                 source_player=m.group(1), dest_player=m.group(1))),

            # P achieves [A] CARD. — skip (deduced from unaccounted cards)
            (re.compile(rf"^({PP}) achieves \[(\d+)\] (.+?)\.$"),
             lambda m: None),

            # P achieves CARD. (special achievements — skip)
            (re.compile(rf"^({PP}) achieves (.+?)\.$"),
             lambda m: None),

            # P1 transfers [A] CARD from board to P2's board.
            (re.compile(rf"^({PP}) transfers \[(\d+)\] (.+?) from board to ({PP})'s board\.$"),
             lambda m: Action(
                 source="board", dest="board",
                 card_index=m.group(3).lower(),
                 source_player=m.group(1), dest_player=m.group(4))),

            # P1 transfers [A] CARD from P2's board to board.
            (re.compile(rf"^({PP}) transfers \[(\d+)\] (.+?) from ({PP})'s board to board\.$"),
             lambda m: Action(
                 source="board", dest="board",
                 card_index=m.group(3).lower(),
                 source_player=m.group(4), dest_player=m.group(1))),

            # P moves [A] CARD (board -> board). — Compass demand
            (re.compile(rf"^({PP}) moves \[(\d+)\] (.+?) \(board -> board\)\.$"),
             lambda m: Action(
                 source="board", dest="board",
                 card_index=m.group(3).lower(),
                 source_player=m.group(1),
                 dest_player=[p for p in players if p != m.group(1)][0])),
        ]

    def _build_hidden_patterns(self):
        """Build regex patterns for hidden (opponent) card transfers.

        Each entry: (compiled regex, handler function returning Action or None).
        """
        PP = self._pp

        def _parse_hidden(m):
            return m.group(1), (int(m.group(2)), LABEL_TO_SET[m.group(3)])

        def _draw(m):
            player, group_key = _parse_hidden(m)
            return Action(source="deck", dest="hand",
                          group_key=group_key, dest_player=player)

        def _draw_and_score(m):
            player, group_key = _parse_hidden(m)
            return Action(source="deck", dest="score",
                          group_key=group_key, dest_player=player)

        def _return_from_hand(m):
            player, group_key = _parse_hidden(m)
            return Action(source="hand", dest="deck",
                          group_key=group_key, source_player=player)

        def _return_from_board(m):
            player, group_key = _parse_hidden(m)
            return Action(source="board", dest="deck",
                          group_key=group_key, source_player=player)

        def _return_from_score(m):
            player, group_key = _parse_hidden(m)
            return Action(source="score", dest="deck",
                          group_key=group_key, source_player=player)

        def _score_from_hand(m):
            player, group_key = _parse_hidden(m)
            return Action(source="hand", dest="score",
                          group_key=group_key,
                          source_player=player, dest_player=player)

        def _score_from_board(m):
            player, group_key = _parse_hidden(m)
            return Action(source="board", dest="score",
                          group_key=group_key,
                          source_player=player, dest_player=player)

        def _skip(m):
            return None

        def _skip_no_set(m):
            return None

        return [
            # P draws a [N] from base/cities.
            (re.compile(rf"^({PP}) draws a \[(\d+)\] from (base|cities)\.$"),
             _draw),

            # P draws and scores a [N] from base/cities.
            (re.compile(rf"^({PP}) draws and scores a \[(\d+)\] from (base|cities)\.$"),
             _draw_and_score),

            # P returns a [N] from his hand from base/cities.
            (re.compile(rf"^({PP}) returns a \[(\d+)\] from his hand from (base|cities)\.$"),
             _return_from_hand),

            # P returns a [N] from his board from base/cities.
            (re.compile(rf"^({PP}) returns a \[(\d+)\] from his board from (base|cities)\.$"),
             _return_from_board),

            # P returns a [N] from his score pile from base/cities.
            (re.compile(rf"^({PP}) returns a \[(\d+)\] from his score pile from (base|cities)\.$"),
             _return_from_score),

            # P scores a [N] from his hand from base/cities.
            (re.compile(rf"^({PP}) scores a \[(\d+)\] from his hand from (base|cities)\.$"),
             _score_from_hand),

            # P scores a [N] from his board from base/cities.
            (re.compile(rf"^({PP}) scores a \[(\d+)\] from his board from (base|cities)\.$"),
             _score_from_board),

            # P transfers a [N] ... from base/cities. — no-op (complex without names)
            (re.compile(rf"^({PP}) transfers a \[(\d+)\] .+ from (base|cities)\.$"),
             _skip),

            # P achieves a [N] from base/cities. — no-op
            (re.compile(rf"^({PP}) achieves a \[(\d+)\] from (base|cities)\.$"),
             _skip),

            # P achieves [null] CARD. — skip
            (re.compile(rf"^({PP}) achieves \[null\] .+?\.$"),
             _skip_no_set),
        ]

"""StateTracker: log parsing and regex patterns for Innovation game state."""

import json
import re

from bga_tracker.innovation.card import LABEL_TO_SET
from bga_tracker.innovation.game_state import GameState, Action


class StateTracker:
    """Processes an Innovation game log and builds a GameState."""

    def __init__(self, card_db: list[dict], players: list[str], perspective: str):
        self.card_db = card_db
        self.players = players
        self.perspective = perspective
        self.game_state = GameState(card_db, players, perspective)
        self.game_state.init_game(len(players))
        self._player_pattern = "|".join(re.escape(p) for p in players)

    def process_log(self, game_log_path: str) -> "GameState":
        """Read game log JSON, process all entries, return GameState."""
        with open(game_log_path) as f:
            log_data = json.load(f)

        for entry in log_data["log"]:
            self._process_entry(entry)

        return self.game_state

    def _group_key(self, m: re.Match) -> tuple[int, int]:
        return int(m.group(2)), LABEL_TO_SET[m.group(3)]

    def _process_entry(self, entry: dict):
        """Process a single log entry."""
        msg = entry["msg"]
        PP = self._player_pattern

        # AnotherSava reveals his hand: 2 Construction, 2 Philosophy, 2 Fermenting.
        if entry["type"] == "logWithCardTooltips":
            if m := re.match(rf"^({PP}) reveals his hand: (.+)\.$", msg):
                card_names = [part[part.index(" ") + 1:].lower() for part in m.group(2).split(", ")]
                self.game_state.reveal_hand(m.group(1), card_names)
            return

        if entry["type"] != "transfer":
            return

        # --- Hidden patterns (card identity unknown) ---

        # jamdalla draws a [1] from cities.
        if m := re.match(rf"^({PP}) draws a \[(\d+)\] from (base|cities)\.$", msg):
            self.game_state.move(Action(source="deck", dest="hand", group_key=self._group_key(m), dest_player=m.group(1)))

        # jamdalla draws and scores a [6] from base.
        elif m := re.match(rf"^({PP}) draws and scores a \[(\d+)\] from (base|cities)\.$", msg):
            self.game_state.move(Action(source="deck", dest="score", group_key=self._group_key(m), dest_player=m.group(1)))

        # jamdalla returns a [1] from his hand from base.
        elif m := re.match(rf"^({PP}) returns a \[(\d+)\] from his hand from (base|cities)\.$", msg):
            self.game_state.move(Action(source="hand", dest="deck", group_key=self._group_key(m), source_player=m.group(1)))

        # jamdalla returns a [6] from his score pile from base.
        elif m := re.match(rf"^({PP}) returns a \[(\d+)\] from his score pile from (base|cities)\.$", msg):
            self.game_state.move(Action(source="score", dest="deck", group_key=self._group_key(m), source_player=m.group(1)))

        # jamdalla transfers a [5] from his score pile to his hand from base.
        elif m := re.match(rf"^({PP}) transfers a \[(\d+)\] from his score pile to his hand from (base|cities)\.$", msg):
            self.game_state.move(Action(source="score", dest="hand", group_key=self._group_key(m), source_player=m.group(1), dest_player=m.group(1)))

        # jamdalla achieves a [1] from base.
        elif re.match(rf"^({PP}) achieves a \[(\d+)\] from (base|cities)\.$", msg):
            pass  # tracked separately via missing deck cards

        # jamdalla achieves [null] Legend.
        elif re.match(rf"^({PP}) achieves \[null\] .+?\.$", msg):
            pass  # null achievement — skip

        # --- Named patterns (card name known) ---

        # AnotherSava melds [1] Clothing from hand.
        elif m := re.match(rf"^({PP}) melds \[(\d+)\] (.+?) from hand\.$", msg):
            self.game_state.move(Action(source="hand", dest="board", card_index=m.group(3).lower(), source_player=m.group(1), dest_player=m.group(1)))

        # AnotherSava tucks [1] Metalworking from hand.
        elif m := re.match(rf"^({PP}) tucks \[(\d+)\] (.+?) from hand\.$", msg):
            self.game_state.move(Action(source="hand", dest="board", card_index=m.group(3).lower(), source_player=m.group(1), dest_player=m.group(1)))

        # AnotherSava draws and reveals [1] Metalworking.
        elif m := re.match(rf"^({PP}) draws and reveals \[(\d+)\] (.+?)\.$", msg):
            self.game_state.move(Action(source="deck", dest="revealed", card_index=m.group(3).lower(), dest_player=m.group(1)))

        # AnotherSava places [1] Metalworking in hand.
        elif m := re.match(rf"^({PP}) places \[(\d+)\] (.+?) in hand\.$", msg):
            self.game_state.move(Action(source="revealed", dest="hand", card_index=m.group(3).lower(), source_player=m.group(1), dest_player=m.group(1)))

        # AnotherSava draws [1] Jerusalem.
        elif m := re.match(rf"^({PP}) draws \[(\d+)\] (.+?)\.$", msg):
            self.game_state.move(Action(source="deck", dest="hand", card_index=m.group(3).lower(), dest_player=m.group(1)))

        # jamdalla melds [5] Chemistry.
        elif m := re.match(rf"^({PP}) melds \[(\d+)\] (.+?)\.$", msg):
            self.game_state.move(Action(source="revealed", dest="board", card_index=m.group(3).lower(), source_player=m.group(1), dest_player=m.group(1)))

        # AnotherSava scores [3] Hangzhou from hand.
        elif m := re.match(rf"^({PP}) scores \[(\d+)\] (.+?) from hand\.$", msg):
            self.game_state.move(Action(source="hand", dest="score", card_index=m.group(3).lower(), source_player=m.group(1), dest_player=m.group(1)))

        # AnotherSava scores [5] Coal from board.
        elif m := re.match(rf"^({PP}) scores \[(\d+)\] (.+?) from board\.$", msg):
            self.game_state.move(Action(source="board", dest="score", card_index=m.group(3).lower(), source_player=m.group(1), dest_player=m.group(1)))

        # jamdalla transfers [2] Currency from hand to AnotherSava's hand.
        elif m := re.match(rf"^({PP}) transfers \[(\d+)\] (.+?) from hand to ({PP})'s hand\.$", msg):
            self.game_state.move(Action(source="hand", dest="hand", card_index=m.group(3).lower(), source_player=m.group(1), dest_player=m.group(4)))

        # AnotherSava transfers [2] Currency from hand to jamdalla's score pile.
        elif m := re.match(rf"^({PP}) transfers \[(\d+)\] (.+?) from hand to ({PP})'s score pile\.$", msg):
            self.game_state.move(Action(source="hand", dest="score", card_index=m.group(3).lower(), source_player=m.group(1), dest_player=m.group(4)))

        # AnotherSava returns [6] Vaccination from hand.
        elif m := re.match(rf"^({PP}) returns \[(\d+)\] (.+?) from hand\.$", msg):
            self.game_state.move(Action(source="hand", dest="deck", card_index=m.group(3).lower(), source_player=m.group(1)))

        # AnotherSava draws and scores [8] Socialism.
        elif m := re.match(rf"^({PP}) draws and scores \[(\d+)\] (.+?)\.$", msg):
            self.game_state.move(Action(source="deck", dest="score", card_index=m.group(3).lower(), dest_player=m.group(1)))

        # AnotherSava draws and melds [8] Flight.
        elif m := re.match(rf"^({PP}) draws and melds \[(\d+)\] (.+?)\.$", msg):
            self.game_state.move(Action(source="deck", dest="board", card_index=m.group(3).lower(), dest_player=m.group(1)))

        # AnotherSava moves [1] Agriculture (board -> board).
        elif m := re.match(rf"^({PP}) moves \[(\d+)\] (.+?) \(board -> board\)\.$", msg):
            card_index = m.group(3).lower()
            named_player = m.group(1)
            other_player = [p for p in self.players if p != named_player][0]
            source_player = named_player if any(card_index in c.candidates for c in self.game_state.boards[named_player]) else other_player
            dest_player = other_player if source_player == named_player else named_player
            self.game_state.move(Action(source="board", dest="board", card_index=card_index, source_player=source_player, dest_player=dest_player))

        else:
            raise ValueError(f"Unrecognized transfer pattern: {msg}")


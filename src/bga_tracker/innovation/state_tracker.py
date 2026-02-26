"""StateTracker: structured log processing for Innovation game state."""

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

    def _process_entry(self, entry: dict) -> None:
        """Process a single log entry."""

        if entry["type"] == "logWithCardTooltips":
            msg = entry["msg"]
            if m := re.match(rf"^({self._player_pattern}) reveals his hand: (.+)\.$", msg):
                card_names = [part[part.index(" ") + 1:].lower() for part in m.group(2).split(", ")]
                self.game_state.reveal_hand(m.group(1), card_names)
            return

        if entry["type"] != "transfer":
            return

        if entry.get("to") in ("achievements", "claimed"):
            return

        card_name = entry.get("card_name")
        card_index = card_name.lower() if card_name else None
        group_key = (entry["card_age"], LABEL_TO_SET[entry["card_set"]]) if not card_index else None

        source = entry["from"]
        dest = entry["to"]
        source_player = entry.get("from_owner") if source != "deck" else None
        dest_player = entry.get("to_owner") if dest != "deck" else None

        self.game_state.move(Action(
            source=source, dest=dest,
            card_index=card_index, group_key=group_key,
            source_player=source_player, dest_player=dest_player,
        ))

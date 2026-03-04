"""Regression tests for Innovation game state pipeline.

Reruns track_state and format_state on committed fixture data and asserts
that the output matches the reference files (game_state.json, summary.html).
Fixtures live in tests/innovation/fixtures/ and are always present.
"""

import json
from pathlib import Path

import pytest

from bga_tracker.innovation.card import CardDatabase
from bga_tracker.innovation.config import Config
from bga_tracker.innovation.game_log_processor import GameLogProcessor
from bga_tracker.innovation.game_state import GameStateEncoder
from bga_tracker.innovation import format_state

# Discover table directories: "TABLE_ID opponent" folders under tests/innovation/fixtures/
DATA_DIR = Path(__file__).resolve().parent / "fixtures"
TABLE_DIRS = sorted(DATA_DIR.glob("* *"))

CARD_INFO_PATH = Path(__file__).resolve().parent.parent.parent / "assets" / "card_info.json"

# Config loaded from .env — fixtures were generated with these settings
CONFIG = Config.from_env()


def table_ids():
    """Yield (table_id, opponent, table_dir) for each available table."""
    for d in TABLE_DIRS:
        parts = d.name.split(" ", 1)
        if len(parts) == 2 and (d / "game_log.json").exists():
            yield parts[0], parts[1], d


TABLE_PARAMS = list(table_ids())


@pytest.mark.parametrize("table_id,opponent,table_dir", TABLE_PARAMS,
                         ids=[p[0] for p in TABLE_PARAMS])
def test_track_state(table_id, opponent, table_dir):
    reference = table_dir / "game_state.json"
    expected = reference.read_text(encoding="utf-8")

    card_db = CardDatabase(CARD_INFO_PATH)
    players = [CONFIG.player_name, opponent]
    game_log_path = table_dir / "game_log.json"

    tracker = GameLogProcessor(card_db, players, CONFIG.player_name)
    game_state = tracker.process_log(game_log_path).to_json()

    actual = json.dumps(game_state, indent=2, cls=GameStateEncoder)
    assert actual == expected.rstrip("\n")


@pytest.mark.parametrize("table_id,opponent,table_dir", TABLE_PARAMS,
                         ids=[p[0] for p in TABLE_PARAMS])
def test_format_state(table_id, opponent, table_dir):
    reference = table_dir / "summary.html"
    expected = reference.read_text(encoding="utf-8")

    card_db = CardDatabase(CARD_INFO_PATH)
    tracker = GameLogProcessor(card_db, [CONFIG.player_name, opponent], CONFIG.player_name)
    game_state = tracker.process_log(table_dir / "game_log.json")

    players = [CONFIG.player_name, opponent]
    actual = format_state.SummaryFormatter(game_state, table_id, CONFIG, card_db, players, CONFIG.player_name).render()
    assert actual == expected.rstrip("\n")

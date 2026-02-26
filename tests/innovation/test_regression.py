"""Regression tests for Innovation game state pipeline.

Reruns track_state and format_state on committed fixture data and asserts
that the output matches the reference files (game_state.json, summary.html).
Fixtures live in tests/innovation/fixtures/ and are always present.
"""

import json
from pathlib import Path

import pytest

from bga_tracker.innovation.card import CardDB
from bga_tracker.innovation.state_tracker import StateTracker
from bga_tracker.innovation import track_state, format_state

# Discover table directories: "TABLE_ID opponent" folders under tests/innovation/fixtures/
DATA_DIR = Path(__file__).resolve().parent / "fixtures"
TABLE_DIRS = sorted(DATA_DIR.glob("* *"))

CARDINFO_PATH = Path(__file__).resolve().parent.parent.parent / "assets" / "cardinfo.json"


def table_ids():
    """Yield (table_id, opponent, table_dir) for each available table."""
    for d in TABLE_DIRS:
        parts = d.name.split(" ", 1)
        if len(parts) == 2 and (d / "game_log.json").exists():
            yield parts[0], parts[1], d


TABLE_PARAMS = list(table_ids())


@pytest.fixture(autouse=True)
def _reset_cardinfo_cache():
    """Reset format_state's cached card DB between tests."""
    format_state._cardinfo = None
    format_state._card_by_name = None


@pytest.mark.parametrize("table_id,opponent,table_dir", TABLE_PARAMS,
                         ids=[p[0] for p in TABLE_PARAMS])
def test_track_state(table_id, opponent, table_dir):
    reference = table_dir / "game_state.json"
    expected = reference.read_text(encoding="utf-8")

    card_db = CardDB(CARDINFO_PATH)
    players = [track_state.PERSPECTIVE, opponent]
    game_log_path = table_dir / "game_log.json"

    tracker = StateTracker(card_db, players, track_state.PERSPECTIVE)
    game_state = tracker.process_log(game_log_path).to_json()

    actual = json.dumps(game_state, indent=2)
    assert actual == expected.rstrip("\n")


@pytest.mark.parametrize("table_id,opponent,table_dir", TABLE_PARAMS,
                         ids=[p[0] for p in TABLE_PARAMS])
def test_format_state(table_id, opponent, table_dir):
    reference = table_dir / "summary.html"
    expected = reference.read_text(encoding="utf-8")

    with open(table_dir / "game_state.json") as f:
        state = json.load(f)

    actual = format_state.format_summary(state, table_id)
    assert actual == expected.rstrip("\n")

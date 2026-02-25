"""Regression tests for Innovation game state pipeline.

Reruns track_state and format_state on committed fixture data and asserts
that the output matches the reference files (game_state.json, summary.html).
Fixtures live in tests/innovation/data/ and are always present.
"""

import json
from pathlib import Path

import pytest

from bga_tracker.innovation import track_state, format_state

# Discover table directories: "TABLE_ID opponent" folders under tests/data/
DATA_DIR = Path(__file__).resolve().parent / "data"
TABLE_DIRS = sorted(DATA_DIR.glob("* *"))


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

    card_db = track_state.load_card_database()
    players = [track_state.PERSPECTIVE, opponent]
    game_log_path = table_dir / "game_log.json"

    state, known, deck_stacks, unknown_hand, unknown_score = \
        track_state.parse_log(card_db, players, game_log_path)
    achievements = track_state.deduce_achievements(card_db, state, deck_stacks)
    game_state = track_state.build_player_output(
        card_db, state, known, deck_stacks, players,
        unknown_hand, unknown_score, achievements)

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

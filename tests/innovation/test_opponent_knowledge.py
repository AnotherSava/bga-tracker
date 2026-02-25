"""Unit tests for opponent knowledge model in Innovation game state tracking.

Tests the opponent_knows_exact, opponent_might_suspect, suspect_list_explicit
flags and suspect propagation in GameState._propagate().
"""

import json

import pytest

from bga_tracker.innovation.card import Card, CardDB, SET_BASE
from bga_tracker.innovation.game_state import GameState, Action

ME = "Me"
OPP = "Opponent"
PLAYERS = [ME, OPP]


@pytest.fixture
def card_db(tmp_path):
    """Minimal CardDB with five age-3 base cards — one propagation group."""
    cards = [
        {"name": "Paper", "age": 3, "color": "green", "set": 0},
        {"name": "Compass", "age": 3, "color": "blue", "set": 0},
        {"name": "Education", "age": 3, "color": "yellow", "set": 0},
        {"name": "Alchemy", "age": 3, "color": "purple", "set": 0},
        {"name": "Translation", "age": 3, "color": "red", "set": 0},
    ]
    path = tmp_path / "cardinfo.json"
    path.write_text(json.dumps(cards))
    return CardDB(str(path))


ALL_NAMES = {"paper", "compass", "education", "alchemy", "translation"}


def make_state(card_db):
    """Create empty GameState for testing."""
    return GameState(card_db, PLAYERS, ME)


def make_card(name, age=3, card_set=0, candidates=None,
              opp_knows=False, suspect=None, explicit=False):
    """Create a Card with specified opponent knowledge state."""
    c = Card(age, card_set, candidates or {name})
    c.opponent_knows_exact = opp_knows
    c.opponent_might_suspect = set(suspect) if suspect else set()
    c.suspect_list_explicit = explicit
    return c


class TestBoardPlacement:
    """Board placement sets opponent knowledge."""

    def test_meld_sets_opponent_knowledge(self, card_db):
        gs = make_state(card_db)
        paper = make_card("paper")
        gs.hands[ME].append(paper)
        gs._groups[(3, 0)].append(paper)

        gs.move(Action(
            source="hand", dest="board",
            card_index="paper",
            source_player=ME, dest_player=ME))

        assert paper.opponent_knows_exact is True
        assert paper.opponent_might_suspect == {"paper"}
        assert paper.suspect_list_explicit is True


class TestDrawAndReveal:
    """Draw-and-reveal sets opponent knowledge."""

    def test_draw_and_reveal(self, card_db):
        gs = make_state(card_db)
        card = Card(3, 0, ALL_NAMES)
        gs.decks[(3, 0)] = [card]
        gs._groups[(3, 0)].append(card)

        gs.move(Action(
            source="deck", dest="revealed",
            card_index="paper",
            dest_player=ME))

        assert card.opponent_knows_exact is True
        assert card.opponent_might_suspect == {"paper"}
        assert card.suspect_list_explicit is True


class TestHiddenDrawToOpponent:
    """Hidden draw to opponent's hand."""

    def test_hidden_draw_opponent_knows(self, card_db):
        gs = make_state(card_db)
        card = Card(3, 0, ALL_NAMES)
        gs.decks[(3, 0)] = [card]
        gs._groups[(3, 0)].append(card)

        gs.move(Action(
            source="deck", dest="hand",
            group_key=(3, 0),
            dest_player=OPP))

        assert card.opponent_knows_exact is True
        assert card.opponent_might_suspect == set()
        assert card.suspect_list_explicit is False


class TestNamedDrawNoReveal:
    """Named draw to our hand (no reveal)."""

    def test_named_draw_no_opponent_knowledge(self, card_db):
        gs = make_state(card_db)
        card = Card(3, 0, ALL_NAMES)
        gs.decks[(3, 0)] = [card]
        gs._groups[(3, 0)].append(card)

        gs.move(Action(
            source="deck", dest="hand",
            card_index="paper",
            dest_player=ME))

        assert card.opponent_knows_exact is False
        assert card.opponent_might_suspect == set()


class TestTransferBetweenPlayers:
    """Transfer between players sets reveal."""

    def test_transfer_reveals_card(self, card_db):
        gs = make_state(card_db)
        paper = make_card("paper")
        gs.hands[ME].append(paper)
        gs._groups[(3, 0)].append(paper)

        gs.move(Action(
            source="hand", dest="hand",
            card_index="paper",
            source_player=ME, dest_player=OPP))

        assert paper.opponent_knows_exact is True
        assert paper.opponent_might_suspect == {"paper"}
        assert paper.suspect_list_explicit is True


class TestRevealHand:
    """reveal_hand sets full opponent knowledge."""

    def test_reveal_hand_resolves_and_marks(self, card_db):
        gs = make_state(card_db)

        paper = make_card("paper")
        gs.hands[ME].append(paper)
        gs._groups[(3, 0)].append(paper)

        # Unknown card with compass + education as candidates
        unknown = Card(3, 0, {"compass", "education"})
        gs.hands[ME].append(unknown)
        gs._groups[(3, 0)].append(unknown)

        # Remaining cards resolved elsewhere — complete group prevents
        # hidden singles from misfiring on the incomplete 5-name group.
        for name in ["education", "alchemy", "translation"]:
            c = make_card(name)
            gs.boards[OPP].append(c)
            gs._groups[(3, 0)].append(c)

        gs.reveal_hand(ME, ["paper", "compass"])

        # Paper (was already known)
        assert paper.opponent_knows_exact is True
        assert paper.opponent_might_suspect == {"paper"}
        assert paper.suspect_list_explicit is True

        # Compass (was unknown, now resolved)
        assert unknown.opponent_knows_exact is True
        assert unknown.opponent_might_suspect == {"compass"}
        assert unknown.suspect_list_explicit is True
        assert unknown.candidates == {"compass"}


class TestReturnAllKnown:
    """Named return to deck — opponent knew all matching cards."""

    def test_return_merges_suspects(self, card_db):
        gs = make_state(card_db)

        paper = make_card("paper", opp_knows=True,
                          suspect={"paper"}, explicit=True)
        compass = make_card("compass", opp_knows=True,
                            suspect={"compass"}, explicit=True)
        gs.hands[ME].extend([paper, compass])
        gs.decks[(3, 0)] = []
        gs._groups[(3, 0)].extend([paper, compass])

        gs.move(Action(
            source="hand", dest="deck",
            card_index="paper",
            source_player=ME))

        # Suspects merged, certainty lost
        for card in [paper, compass]:
            assert card.opponent_knows_exact is False
            assert card.opponent_might_suspect == {"paper", "compass"}
            assert card.suspect_list_explicit is True

        # Candidates unchanged — we know which card was returned
        assert paper.candidates == {"paper"}
        assert compass.candidates == {"compass"}


class TestReturnPartialKnowledge:
    """Named return to deck — opponent knew some matching cards."""

    def test_return_partial_suspects(self, card_db):
        gs = make_state(card_db)

        paper = make_card("paper", opp_knows=True,
                          suspect={"paper"}, explicit=True)
        unknown = Card(3, 0, {"compass", "education"})
        # unknown has opp_knows=False, suspect=None by default

        gs.hands[ME].extend([paper, unknown])
        gs.decks[(3, 0)] = []
        gs._groups[(3, 0)].extend([paper, unknown])

        gs.move(Action(
            source="hand", dest="deck",
            card_index="paper",
            source_player=ME))

        for card in [paper, unknown]:
            assert card.opponent_knows_exact is False
            assert card.opponent_might_suspect == {"paper"}
            assert card.suspect_list_explicit is False


class TestSuspectPropagation:
    """Suspect propagation: the full Oars -> discard -> re-reveal scenario."""

    def test_reveal_triggers_suspect_deduction(self, card_db):
        gs = make_state(card_db)

        # Post-named-return state: candidates known, suspects merged
        card_a = Card(3, 0, {"compass"})
        card_a.opponent_knows_exact = False
        card_a.opponent_might_suspect = {"paper", "compass"}
        card_a.suspect_list_explicit = True

        card_b = Card(3, 0, {"paper"})
        card_b.opponent_knows_exact = False
        card_b.opponent_might_suspect = {"paper", "compass"}
        card_b.suspect_list_explicit = True

        gs.hands[ME].append(card_a)
        gs.decks[(3, 0)] = [card_b]
        gs._groups[(3, 0)].extend([card_a, card_b])

        # Reveal shows card_a is Compass; suspect propagation deduces card_b
        gs.reveal_hand(ME, ["compass"])

        # Card A: revealed as Compass
        assert card_a.candidates == {"compass"}
        assert card_a.opponent_knows_exact is True
        assert card_a.opponent_might_suspect == {"compass"}
        assert card_a.suspect_list_explicit is True

        # Card B: deduced via suspect propagation
        assert card_b.candidates == {"paper"}
        assert card_b.opponent_knows_exact is True
        assert card_b.opponent_might_suspect == {"paper"}
        assert card_b.suspect_list_explicit is True

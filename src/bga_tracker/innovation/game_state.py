"""GameState class: locations, mutations, constraint propagation."""

from dataclasses import dataclass
from collections import defaultdict
from itertools import combinations

from bga_tracker.innovation.card import Card, CardDB, SET_BASE, SET_LABEL


@dataclass
class Action:
    """Uniform representation of any card movement."""
    source: str = ""                # "deck", "hand", "board", "score", "revealed" — always set
    dest: str = ""                  # "deck", "hand", "board", "score", "revealed" — always set
    card_index: str | None = None           # lowercase index name, None for hidden actions
    group_key: tuple[int, int] | None = None  # (age, card_set), None for named actions
    source_player: str | None = None
    dest_player: str | None = None


class GameState:
    """Tracks the complete state of an Innovation game.

    Maintains card locations (decks, hands, boards, scores, achievements)
    as lists of Card objects, with constraint propagation to narrow down
    unknown card identities.
    """

    def __init__(self, card_db: CardDB, players: list[str], perspective: str) -> None:
        self.card_db = card_db
        self.players = players
        self.perspective = perspective

        self.decks = {}           # (age, card_set) -> [Card], index 0 = top
        self.hands = {p: [] for p in players}
        self.boards = {p: [] for p in players}
        self.scores = {p: [] for p in players}
        self.revealed = {p: [] for p in players}  # transient zone for draw-and-reveal
        self.achievements = []    # 9 slots (ages 1-9)

        # All Card objects per (age, card_set) group — for propagation
        self._groups: dict[tuple[int, int], list[Card]] = defaultdict(list)

    def _create_card(self, group_key: tuple[int, int], index_names: set[str]) -> Card:
        """Create a Card and register it in the propagation group."""
        c = Card(*group_key, index_names)
        self._groups[group_key].append(c)
        return c

    def init_game(self, num_players: int) -> None:
        """Set up initial game state: all cards in decks, then deal."""
        # Create all cards in decks
        groups = defaultdict(set)
        for card in self.card_db.values():
            groups[card.group_key].add(card.index_name)

        for group_key, index_names in groups.items():
            self.decks[group_key] = [self._create_card(group_key, index_names) for _ in range(len(index_names))]

        # Move 1 card per base age 1-9 to achievements
        for age in range(1, 10):
            deck = self.decks[(age, SET_BASE)]
            self.achievements.append(deck.pop())

        # Deal 2 base age-1 cards per player
        deck = self.decks[(1, SET_BASE)]
        for p in self.players:
            for _ in range(2):
                self.hands[p].append(deck.pop())

    # ------------------------------------------------------------------
    # Location helpers
    # ------------------------------------------------------------------

    def _cards_at(self, loc_type: str, player: str | None, group_key: tuple[int, int]) -> list[Card]:
        """Return the card list for a location type."""
        match loc_type:
            case "deck":
                return self.decks[group_key]
            case "hand":
                return self.hands[player]
            case "board":
                return self.boards[player]
            case "score":
                return self.scores[player]
            case "revealed":
                return self.revealed[player]
            case _:
                raise ValueError(f"Unknown location type: {loc_type}")

    # ------------------------------------------------------------------
    # Mutation
    # ------------------------------------------------------------------

    def _take_from_source(self, action: Action, group_key: tuple[int, int]) -> Card:
        """Find, resolve, remove, and merge at the source location."""
        if action.source == "deck":
            source_cards = self.decks[group_key]
            card = source_cards[0]
        else:
            source_cards = self._cards_at(action.source, action.source_player, group_key)
            if action.card_index:
                card: Card = next(c for c in source_cards if action.card_index in c.candidates)
            else:
                card: Card = next(c for c in source_cards if c.group_key == group_key)

        if action.card_index and not card.is_resolved:
            card.resolve(action.card_index)
            self._propagate(group_key)

        source_cards.remove(card)

        # Hidden action from private zone: we can't tell which card moved
        if not action.card_index and action.source in ("hand", "score"):
            self._merge_candidates(card, source_cards)

        self._merge_suspects(card, source_cards, action)

        return card

    def _update_opponent_knowledge(self, card: Card, action: Action) -> None:
        """Update opponent knowledge flags after a move."""
        is_visible_to_both = (action.dest in ("board", "revealed")
                              or (action.source_player is not None
                                  and action.dest_player is not None
                                  and action.source_player != action.dest_player))
        if is_visible_to_both:
            card.mark_public()
            return

        is_visible_to_opponent = action.dest in ("hand", "score") and action.dest_player != self.perspective
        if is_visible_to_opponent:
            card.opponent_knows_exact = True

    def move(self, action: Action) -> None:
        """Move a card from one location to another."""

        group_key = self.card_db[action.card_index].group_key if action.card_index else action.group_key

        card = self._take_from_source(action, group_key)
        self._cards_at(action.dest, action.dest_player, group_key).append(card)
        self._update_opponent_knowledge(card, action)

    def _merge_candidates(self, card: Card, remaining_source: list[Card]) -> None:
        """Merge candidate sets when we can't tell which card moved.

        The moved card and remaining same-group cards at the source all
        become ambiguous: each gets the union of all their candidates.
        """
        affected = [card] + [c for c in remaining_source if c.group_key == card.group_key]
        if len(affected) <= 1:
            return
        union = {name for c in affected for name in c.candidates}
        for c in affected:
            c.candidates = set(union)

    def _merge_suspects(self, card: Card, remaining_source: list[Card], action: Action) -> None:
        """Merge suspect lists when opponent can't tell which card moved.

        The moved card and remaining same-group cards at the source all
        lose opponent certainty: each gets the union of all their suspects.
        """
        # Only relevant when our card moves between private zones —
        # opponent can't see which card left, so they lose certainty.
        if not (action.source in ("hand", "score")
                and action.dest in ("deck", "hand", "score")
                and action.source_player == self.perspective
                and action.dest_player in (None, self.perspective)):
            return

        affected = [card] + [c for c in remaining_source if c.group_key == card.group_key]
        if len(affected) == 1:
            return

        # Collect all names the opponent could associate with these cards.
        suspect_union = {name for c in affected for name in c.opponent_might_suspect}

        # The merged suspect list is "explicit" (closed/complete) only if
        # every card's suspect list was already closed before the merge.
        all_explicit = all(c.suspect_list_explicit for c in affected)

        # All cards lose certainty — opponent can't tell which one moved
        for c in affected:
            c.opponent_knows_exact = False
            c.opponent_might_suspect = set(suspect_union)
            c.suspect_list_explicit = all_explicit

    def reveal_hand(self, player: str, card_indices: list[str]) -> None:
        """Handle 'reveals his hand' — resolve and mark cards without moving them."""
        for card_index in card_indices:
            group_key = self.card_db[card_index].group_key

            card: Card = next(c for c in self.hands[player] if card_index in c.candidates)
            card.resolve(card_index)
            card.mark_public()
            self._propagate(group_key)

    # ------------------------------------------------------------------
    # Constraint propagation
    # ------------------------------------------------------------------

    def _propagate(self, group_key: tuple[int, int]) -> None:
        """Propagate constraints within an (age, card_set) group to fixed-point.

        1. Singleton propagation: resolved card's index removed from all others.
        2. Hidden singles: name in only 1 card's candidates → resolve.
        3. Naked subsets: N cards with exactly N candidates → remove from others.
        4. Suspect propagation: publicly-known names removed from suspect lists.
           If explicit suspect list → 1 element → opponent_knows_exact.
        """
        group = self._groups[group_key]
        changed = True
        while changed:
            changed = False

            # 1. Singleton propagation
            for card in group:
                if card.is_resolved:
                    for other in group:
                        if other is not card and card.card_index in other.candidates:
                            other.candidates.discard(card.card_index)
                            if other.is_resolved:
                                changed = True

            # 2. Hidden singles
            for candidate_name in {name for c in group if not c.is_resolved for name in c.candidates}:
                holders = [c for c in group if candidate_name in c.candidates and not c.is_resolved]
                if len(holders) == 1:
                    holders[0].resolve(candidate_name)
                    changed = True

            # 3. Naked subsets (only for small groups — max 15)
            unresolved = [c for c in group if not c.is_resolved]
            if len(unresolved) > 3:
                for size in range(2, len(unresolved)):
                    for subset in combinations(unresolved, size):
                        union = {name for c in subset for name in c.candidates}
                        if len(union) == size:
                            for other in unresolved:
                                if other not in subset:
                                    other.candidates -= union
                                    if other.is_resolved:
                                        changed = True
                            break  # restart after changes

            # 4. Suspect propagation: remove publicly-known names from
            #    other cards' suspect lists within the same group.
            for card in group:
                if card.opponent_knows_exact and card.is_resolved:
                    for other in group:
                        if other is not card and card.card_index in other.opponent_might_suspect:
                            other.opponent_might_suspect.discard(card.card_index)
                            if other.suspect_list_explicit and len(other.opponent_might_suspect) == 1:
                                other.opponent_knows_exact = True
                                changed = True

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_json(self) -> dict:
        """Produce game state dict matching the current JSON format.

        Resolved cards → {"name": display_name, "revealed": false}
        Unresolved cards → {"age": int, "set": int}
        Board cards → {"name": display_name}
        Deck entries → null or {"name": display_name, "revealed": false}
        Achievements → {"name": display_name} or null
        """
        result = {
            "actual_deck": {},
            "board": {p: [] for p in self.players},
            "hand": {p: [] for p in self.players},
            "score": {p: [] for p in self.players},
            "achievements": [],
        }

        for p in self.players:
            # Board: normally always known; unresolved cards sorted to end
            known_board = [c for c in self.boards[p] if c.is_resolved]
            unknown_board = [c for c in self.boards[p]
                            if not c.is_resolved and len(c.candidates) != 0]
            board_entries = [
                {"name": self.card_db.display_name(c.card_index)}
                for c in sorted(known_board,
                                key=lambda c: self.card_db.sort_key(c.card_index))
            ]
            for c in sorted(unknown_board, key=lambda c: (c.age, c.card_set)):
                board_entries.append({"age": c.age, "set": c.card_set})
            result["board"][p] = board_entries

            # Hand: known cards first (sorted), then unknowns (sorted)
            hand_named = sorted(
                [c for c in self.hands[p] if c.is_resolved],
                key=lambda c: self.card_db.sort_key(c.card_index))
            hand_unknown = sorted(
                [c for c in self.hands[p]
                 if not c.is_resolved and len(c.candidates) != 0],
                key=lambda c: (c.age, c.card_set))
            hand_entries = []
            for c in hand_named:
                hand_entries.append({
                    "name": self.card_db.display_name(c.card_index),
                    "revealed": False,
                })
            for c in hand_unknown:
                hand_entries.append({"age": c.age, "set": c.card_set})
            result["hand"][p] = hand_entries

            # Score: same logic as hand
            score_named = sorted(
                [c for c in self.scores[p] if c.is_resolved],
                key=lambda c: self.card_db.sort_key(c.card_index))
            score_unknown = sorted(
                [c for c in self.scores[p]
                 if not c.is_resolved and len(c.candidates) != 0],
                key=lambda c: (c.age, c.card_set))
            score_entries = []
            for c in score_named:
                score_entries.append({
                    "name": self.card_db.display_name(c.card_index),
                    "revealed": False,
                })
            for c in score_unknown:
                score_entries.append({"age": c.age, "set": c.card_set})
            result["score"][p] = score_entries

        # Decks — only ages with cards remaining
        for (age, card_set), stack in sorted(self.decks.items()):
            if not stack:
                continue
            age_str = str(age)
            if age_str not in result["actual_deck"]:
                result["actual_deck"][age_str] = {"base": [], "cities": []}
            label = SET_LABEL[card_set]
            entries = []
            for card in stack:
                if card.is_resolved:
                    entries.append({
                        "name": self.card_db.display_name(card.card_index),
                        "revealed": False,
                    })
                else:
                    entries.append(None)
            result["actual_deck"][age_str][label] = entries

        # Achievements (ages 1-9): deduce from remaining hidden base cards.
        # For each age, if exactly one base card is unaccounted for,
        # that card must be the achievement.
        accounted = set()  # card indices with resolved identity somewhere
        for p in self.players:
            for c in self.hands[p]:
                if c.is_resolved:
                    accounted.add(c.card_index)
            for c in self.boards[p]:
                if c.is_resolved:
                    accounted.add(c.card_index)
            for c in self.scores[p]:
                if c.is_resolved:
                    accounted.add(c.card_index)
        for stack in self.decks.values():
            for c in stack:
                if c.is_resolved:
                    accounted.add(c.card_index)

        for age in range(1, 10):
            group_names = self.names_for_group(age, SET_BASE)
            hidden = [n for n in group_names if n not in accounted]
            if len(hidden) == 1:
                result["achievements"].append(
                    {"name": self.card_db.display_name(hidden[0])})
            else:
                result["achievements"].append(None)

        return result

    def names_for_group(self, age: int, card_set: int) -> list[str]:
        return [card.card_index for card in self._groups.get((age, card_set), [])]
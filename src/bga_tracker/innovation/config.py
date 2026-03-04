"""Configuration for Innovation game state tools.

Reads settings from .env file and environment variables. Provides a Config
dataclass with validated fields and sensible defaults.
"""

import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

from bga_tracker import PROJECT_ROOT

_SECTION_IDS = [
    "hand-opponent", "hand-me", "score-opponent", "score-me",
    "achievements", "base-deck", "cities-deck", "base-list", "cities-list",
]
_SECTION_DEFAULTS = {sid: f"1.{i+1}" for i, sid in enumerate(_SECTION_IDS)}

_VALID_VISIBILITY = {"show", "hide", "none"}
_VALID_VISIBILITY_UNKNOWN = {"show", "hide", "none", "unknown"}
_VALID_LAYOUT = {"wide", "tall"}


@dataclass
class Config:
    """Innovation tool configuration."""

    player_name: str
    hand_opponent: str = "show"
    hand_me: str = "show"
    score_opponent: str = "show"
    score_me: str = "show"
    base_deck: str = "show"
    cities_deck: str = "hide"
    base_list: str = "none"
    cities_list: str = "none"
    base_list_layout: str = "wide"
    cities_list_layout: str = "wide"
    achievements: str = "show"
    achievements_layout: str = "wide"
    section_positions: dict[str, tuple[int, float]] = field(default_factory=lambda: {sid: (1, float(f"1.{i+1}")) for i, sid in enumerate(_SECTION_IDS)})

    def __post_init__(self) -> None:
        if not self.player_name:
            raise ValueError("player_name is required")
        self.hand_opponent = self._validate(self.hand_opponent, _VALID_VISIBILITY, "hand_opponent")
        self.hand_me = self._validate(self.hand_me, _VALID_VISIBILITY, "hand_me")
        self.score_opponent = self._validate(self.score_opponent, _VALID_VISIBILITY, "score_opponent")
        self.score_me = self._validate(self.score_me, _VALID_VISIBILITY, "score_me")
        self.base_deck = self._validate(self.base_deck, _VALID_VISIBILITY, "base_deck")
        self.cities_deck = self._validate(self.cities_deck, _VALID_VISIBILITY, "cities_deck")
        self.base_list = self._validate(self.base_list, _VALID_VISIBILITY_UNKNOWN, "base_list")
        self.cities_list = self._validate(self.cities_list, _VALID_VISIBILITY_UNKNOWN, "cities_list")
        self.base_list_layout = self._validate(self.base_list_layout, _VALID_LAYOUT, "base_list_layout")
        self.cities_list_layout = self._validate(self.cities_list_layout, _VALID_LAYOUT, "cities_list_layout")
        self.achievements = self._validate(self.achievements, _VALID_VISIBILITY, "achievements")
        self.achievements_layout = self._validate(self.achievements_layout, _VALID_LAYOUT, "achievements_layout")

    @staticmethod
    def _parse_section_positions() -> dict[str, tuple[int, float]]:
        """Parse SECTION_* env vars into {section_id: (column, position)} dict."""
        positions = {}
        for sid in _SECTION_IDS:
            env_name = f"SECTION_{sid.upper().replace('-', '_')}"
            val = os.environ.get(env_name, _SECTION_DEFAULTS[sid])
            positions[sid] = (int(val.split(".", 1)[0]), float(val))
        return positions

    @staticmethod
    def _validate(value: str, valid: set[str], field_name: str) -> str:
        normalized = value.lower()
        if normalized not in valid:
            raise ValueError(f"Invalid {field_name}={value!r}, expected one of {sorted(valid)}")
        return normalized

    @classmethod
    def from_env(cls) -> "Config":
        """Load config from .env file and environment variables."""
        load_dotenv(PROJECT_ROOT / ".env")
        player_name = os.environ.get("PLAYER_NAME", "")
        return cls(
            player_name=player_name,
            hand_opponent=os.environ.get("DEFAULT_HAND_OPPONENT", "show"),
            hand_me=os.environ.get("DEFAULT_HAND_ME", "show"),
            score_opponent=os.environ.get("DEFAULT_SCORE_OPPONENT", "show"),
            score_me=os.environ.get("DEFAULT_SCORE_ME", "show"),
            base_deck=os.environ.get("DEFAULT_BASE_DECK", "show"),
            cities_deck=os.environ.get("DEFAULT_CITIES_DECK", "hide"),
            base_list=os.environ.get("DEFAULT_BASE_LIST", "none"),
            cities_list=os.environ.get("DEFAULT_CITIES_LIST", "none"),
            base_list_layout=os.environ.get("DEFAULT_BASE_LIST_LAYOUT", "wide"),
            cities_list_layout=os.environ.get("DEFAULT_CITIES_LIST_LAYOUT", "wide"),
            achievements=os.environ.get("DEFAULT_ACHIEVEMENTS", "show"),
            achievements_layout=os.environ.get("DEFAULT_ACHIEVEMENTS_LAYOUT", "wide"),
            section_positions=cls._parse_section_positions(),
        )

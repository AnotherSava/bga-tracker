"""Shared path constants and directory lookup for Innovation tools."""

from pathlib import Path

from bga_tracker import PROJECT_ROOT

DATA_DIR = PROJECT_ROOT / "data"
ASSETS_DIR = PROJECT_ROOT / "assets"
CARD_INFO_PATH = ASSETS_DIR / "card_info.json"
TEMPLATE_DIR = PROJECT_ROOT / "templates" / "innovation"


def find_table(table_id: str) -> tuple[Path, str]:
    """Find table data directory and opponent name from 'TABLE_ID opponent' folder."""
    matches = list(DATA_DIR.glob(f"{table_id} *"))
    if len(matches) != 1:
        raise FileNotFoundError(f"No unique table directory for '{table_id}' in {DATA_DIR}")
    table_dir = matches[0]
    opponent = table_dir.name.split(" ", 1)[1]
    return table_dir, opponent

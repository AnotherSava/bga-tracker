"""
Download BGA Innovation sprite sheets and extract individual icon PNGs.

Downloads sprites from the bga-innovation GitHub repo, then uses Pillow
to extract individual resource icons, hexagon icons, bonus icons, and
cities special icons.

Usage: python scripts/download_assets.py
"""

import json
import urllib.request
from pathlib import Path

from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ASSETS_DIR = PROJECT_ROOT / "assets"
SPRITES_DIR = ASSETS_DIR / "sprites"
ICONS_DIR = ASSETS_DIR / "icons"
DATA_DIR = PROJECT_ROOT / "data"

BASE_URL = "https://raw.githubusercontent.com/micahstairs/bga-innovation/main-dev/img/"

SPRITES = [
    "resource_icons.jpg",
    "hexagon_icons.png",
    "bonus_icons.png",
    "cities_special_icons.png",
]

ICON_NAMES = {1: "crown", 2: "leaf", 3: "lightbulb", 4: "castle", 5: "factory", 6: "clock"}
COLOR_NAMES = {0: "blue", 1: "red", 2: "green", 3: "yellow", 4: "purple"}
COLOR_ORDER = {"blue": 0, "red": 1, "green": 2, "yellow": 3, "purple": 4}


def download_sprites():
    """Download sprite sheets from BGA GitHub."""
    SPRITES_DIR.mkdir(parents=True, exist_ok=True)
    for filename in SPRITES:
        dest = SPRITES_DIR / filename
        if dest.exists():
            print(f"  Already exists: {dest.name}")
            continue
        url = BASE_URL + filename
        print(f"  Downloading {filename}...")
        urllib.request.urlretrieve(url, dest)


def extract_resource_icons():
    """Extract 30 individual resource icons (6 types x 5 colors).

    Sprite layout: 6 columns (icon types 1-6) x 5 rows (colors 0-4).
    CSS M-size: background-size 230px, icon 36x36.
    """
    sprite = Image.open(SPRITES_DIR / "resource_icons.jpg")
    w, h = sprite.size
    scale = w / 230

    # CSS background-position values at 230px scale (negated = pixel offset)
    css_x = [1, 39.5, 78, 116, 154.5, 192.5]
    css_y = [1, 39.5, 78, 116, 154.5]
    icon_px = round(36 * scale)

    count = 0
    for icon_idx, icon_name in ICON_NAMES.items():
        col = icon_idx - 1
        for color_idx, color_name in COLOR_NAMES.items():
            x = round(css_x[col] * scale)
            y = round(css_y[color_idx] * scale)
            icon = sprite.crop((x, y, x + icon_px, y + icon_px))
            icon.save(ICONS_DIR / f"{icon_name}_{color_name}.png")
            count += 1

    print(f"  Extracted {count} resource icons")


def load_cardinfo():
    with open(DATA_DIR / "cardinfo.json") as f:
        return json.load(f)


def extract_hex_icons():
    """Extract hexagon icons for base and cities cards.

    Sprite layout: 15 columns, variable rows.
    CSS M-size: background-size 735px, offset 49px, start 3px, icon 45x45.
    Base cards (indices 0-104): row 0 has 15 cols, rows 1-9 have 10 cols.
    Cities cards share cols 10-14 in rows 1-9 (and row 12 for age 10).
    """
    sprite = Image.open(SPRITES_DIR / "hexagon_icons.png")
    w, h = sprite.size
    scale = w / 735
    offset = 49 * scale
    start = 3 * scale
    icon_px = round(45 * scale)

    cards = load_cardinfo()

    # --- Base cards (set 0) ---
    base = [(i, c) for i, c in enumerate(cards) if c and c.get("set") == 0]
    sorted_base = sorted(
        base, key=lambda x: (x[1]["age"], COLOR_ORDER[x[1]["color"]], x[0])
    )

    for sprite_idx, (cardnum, _card) in enumerate(sorted_base):
        if sprite_idx < 15:
            row, col = 0, sprite_idx
        else:
            row = 1 + (sprite_idx - 15) // 10
            col = (sprite_idx - 15) % 10

        x = round(start + col * offset)
        y = round(start + row * offset)
        icon = sprite.crop((x, y, x + icon_px, y + icon_px))
        icon.save(ICONS_DIR / f"hex_{cardnum}.png")

    print(f"  Extracted {len(sorted_base)} base hex icons")

    # --- Cities cards (set 3) ---
    cities = [(i, c) for i, c in enumerate(cards) if c and c.get("set") == 3]
    sorted_cities = sorted(
        cities, key=lambda x: (x[1]["age"], COLOR_ORDER[x[1]["color"]], x[0])
    )

    for sprite_idx, (cardnum, _card) in enumerate(sorted_cities):
        icon_num = 220 + sprite_idx
        if icon_num <= 234:  # age 1: 15 cards, 3 per color column
            row = 1
            col = 10 + (icon_num - 220) // 3
        elif icon_num <= 314:  # ages 2-9: 80 cards, 2 per color column
            row = 2 + (icon_num - 235) // 10
            col = 10 + ((icon_num - 235) % 10) // 2
        else:  # age 10: 10 cards, 2 per color column
            row = 12
            col = 10 + (icon_num - 315) // 2

        x = round(start + col * offset)
        y = round(start + row * offset)
        icon = sprite.crop((x, y, x + icon_px, y + icon_px))
        icon.save(ICONS_DIR / f"hex_{cardnum}.png")

    print(f"  Extracted {len(sorted_cities)} cities hex icons")


def extract_bonus_icons():
    """Extract bonus number icons (1-11).

    Sprite layout: bonus values in second row.
    CSS M-size: background-size 230px, icon 20x22, y-offset 40px.
    X positions from compiled SCSS exponential formula.
    """
    sprite = Image.open(SPRITES_DIR / "bonus_icons.png")
    w, h = sprite.size
    scale = w / 230

    icon_w = round(20 * scale)
    icon_h = round(22 * scale)
    y = round(40 * scale)

    # Sprite X positions (absolute pixel offsets at 230px scale)
    bonus_x = {
        1: 0,
        2: 20.122,
        3: 41.175,
        4: 62.196,
        5: 83.195,
        6: 104.175,
        7: 125.140,
        8: 146.093,
        9: 167.034,
        10: 187.965,
        11: 208.887,
    }

    for num, css_x in bonus_x.items():
        x = round(css_x * scale)
        icon = sprite.crop((x, y, x + icon_w, y + icon_h))
        icon.save(ICONS_DIR / f"bonus_{num}.png")

    print(f"  Extracted {len(bonus_x)} bonus icons")


def extract_cities_special_icons():
    """Extract cities special icons (flags, arrows, plus).

    Sprite layout: 5 columns (colors) x 4 rows + search row.
    CSS M-size: background-size 230px, icon 40x40.
    """
    sprite = Image.open(SPRITES_DIR / "cities_special_icons.png")
    w, h = sprite.size
    scale = w / 230
    icon_px = round(40 * scale)

    css_x = [1, 42, 83, 124, 165]  # per color column
    css_y = [1, 42, 83, 124]  # 4 icon rows

    # Row-to-name mapping (best guess from SCSS icon numbers + game data)
    # Row 0 = plus, Row 1 = arrows (left/right/up share), Row 2 = blackflag, Row 3 = whiteflag
    row_names = ["plus", "arrow", "blackflag", "whiteflag"]

    count = 0
    for row_idx, icon_name in enumerate(row_names):
        for color_idx, color_name in COLOR_NAMES.items():
            x = round(css_x[color_idx] * scale)
            y = round(css_y[row_idx] * scale)
            icon = sprite.crop((x, y, x + icon_px, y + icon_px))
            icon.save(ICONS_DIR / f"{icon_name}_{color_name}.png")
            count += 1

    print(f"  Extracted {count} cities special icons")


CARDS_DIR = ASSETS_DIR / "cards"
CARDS_BASE_URL = "https://raw.githubusercontent.com/micahstairs/bga-innovation/main-dev/misc/cards/"

# Card image sorting: Red=0, Yellow=1, Green=2, Blue=3, Purple=4
CARD_IMG_COLOR_ORDER = {"red": 0, "yellow": 1, "green": 2, "blue": 3, "purple": 4}
TOOLTIP_WIDTH = 375  # half of original 750px


def download_card_images():
    """Download card face images for base and cities sets, resize for tooltips.

    Images are sorted by (age, color, name) where color order is R,Y,G,B,P.
    Base: Print_BaseCards_front-001.png to -105.png (+ 7 extras we skip)
    Cities: Print_CitiesCards_front-001.png to -105.png (+ 7 extras)
    """
    CARDS_DIR.mkdir(parents=True, exist_ok=True)
    cards = load_cardinfo()

    for set_id, set_name in [(0, "Base"), (3, "Cities")]:
        set_cards = [(i, c) for i, c in enumerate(cards) if c and c.get("set") == set_id]
        sorted_cards = sorted(
            set_cards,
            key=lambda x: (x[1]["age"], CARD_IMG_COLOR_ORDER[x[1]["color"]], x[1]["name"])
        )

        folder = f"Print_{set_name}Cards_front"
        count = 0
        for img_idx, (cardnum, _card) in enumerate(sorted_cards):
            dest = CARDS_DIR / f"card_{cardnum}.png"
            if dest.exists():
                count += 1
                continue
            img_num = f"{img_idx + 1:03d}"
            url = f"{CARDS_BASE_URL}{folder}/{folder}-{img_num}.png"
            print(f"  Downloading {folder}-{img_num}.png -> card_{cardnum}.png")
            try:
                urllib.request.urlretrieve(url, dest)
                count += 1
            except Exception as e:
                print(f"    Error: {e}")

        print(f"  {set_name}: {count} card images")


def main():
    ICONS_DIR.mkdir(parents=True, exist_ok=True)

    print("Step 1: Downloading sprites...")
    download_sprites()

    print("Step 2: Extracting resource icons...")
    extract_resource_icons()

    print("Step 3: Extracting hex icons...")
    extract_hex_icons()

    print("Step 4: Extracting bonus icons...")
    extract_bonus_icons()

    print("Step 5: Extracting cities special icons...")
    extract_cities_special_icons()

    print("Step 6: Downloading card images...")
    download_card_images()

    print("Done!")


if __name__ == "__main__":
    main()

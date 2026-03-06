# BGA Innovation Tracker

A Chrome extension that tracks hidden card information in [Innovation](https://boardgamegeek.com/boardgame/63888/innovation) games on [Board Game Arena](https://boardgamearena.com). No more struggling to remember deck stack order, opponent hand contents, or revealed cards.

## Features

- Extracts game data directly from BGA game pages
- Tracks all card movements, deck stack order, and opponent knowledge
- Constraint propagation deduces hidden card identities (singleton elimination, hidden singles, naked subsets)
- Colored HTML summary in a Chrome side panel with card tooltips
- Download buttons for game_log.json, game_state.json, and self-contained summary.html

## Setup

### Prerequisites

- Node.js 18+
- Chrome 128+

### Install

```
npm install
npm run build
```

### Load Extension

1. Open Chrome and navigate to `chrome://extensions`
2. Enable "Developer mode" (toggle in the top-right corner)
3. Click "Load unpacked" and select this project's root directory
4. The Innovation tracker icon appears in the Chrome toolbar

## Usage

1. Navigate to a BGA Innovation game page in Chrome
2. Click the Innovation tracker icon in the toolbar
   - Badge shows "..." while extracting
   - Badge shows a green checkmark on success
   - Badge shows red "ERR" on failure
3. The side panel opens with a visual summary of the game state
4. Use the download toolbar to save game_log.json, game_state.json, or summary.html

### Summary Features

- Card grids showing hand, score, board, deck, and full card lists
- Visibility toggles: None / All / Unknown (show only unaccounted cards)
- Layout toggles: Wide (one row per age) / Tall (color columns)
- Hover tooltips: card face images for base cards, name and dogma text for cities
- Dark theme with color-coded cards (blue, red, green, yellow, purple)

## Development

```
npm run dev          # Watch mode (rebuilds on changes)
npm test             # Run tests
npm run test:watch   # Watch mode tests
npm run lint         # TypeScript type checking
```

## Architecture

```
manifest.json          Chrome extension manifest (v3, side panel)
sidepanel.html         Side panel page shell (Vite HTML entry point)
src/
  background.ts        Service worker: pipeline orchestration, side panel management
  extract.ts           Content script: BGA data extraction (MAIN world)
  sidepanel/
    sidepanel.ts       Receives data, triggers render, handles downloads
    sidepanel.css      Dark theme, card grids, tooltips
  models/
    types.ts           Type definitions: Card, CardInfo, GameState, Action, enums
  engine/
    process_log.ts     Raw BGA packets -> structured game log
    game_state.ts      State tracking + constraint propagation
  render/
    summary.ts         GameState -> HTML string via template literals
    config.ts          Section layout config, visibility/layout defaults
assets/
  card_info.json       Card database (210 cards: 105 base + 105 cities)
  icons/               Resource and hex icon PNGs
  cards/               Full card face images (for tooltips)
  sprites/             Card sprite sheets
```

Data flow:
1. User clicks extension icon on a BGA Innovation game page
2. extract.ts (MAIN world) fetches game data from BGA internals
3. background.ts receives data, runs pipeline (processRawLog -> GameState)
4. background.ts opens side panel, sends results via chrome.runtime messaging
5. sidepanel.ts renders summary with download buttons

## Testing

Tests use vitest and cover the full pipeline: types, log processing, game state engine, rendering, and extension entry points.

```
npm test                        # Run all tests
npx vitest run --coverage       # Run with coverage report
```

## Acknowledgments

Card icons and images are from [bga-innovation](https://github.com/micahstairs/bga-innovation), Micah Stairs' BGA implementation of [Innovation](https://boardgamegeek.com/boardgame/63888/innovation) (Carl Chudyk, Asmadi Games).

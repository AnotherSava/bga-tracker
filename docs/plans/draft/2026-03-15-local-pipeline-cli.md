# Local pipeline CLI runner

## Status: DRAFT — design discussion in progress

## Overview

A single CLI script that runs any segment of the extension's transformation pipeline locally, so debugging doesn't require ad-hoc throwaway scripts each time. Accepts a stage name and input file(s), runs the corresponding functions, and writes output to the same directory.

## Context

The extension pipeline has 4 stages, each independently testable:
1. `processRawLog(rawData)` → `GameLog`
2. `GameState` constructor + `processLog()` → `toJSON()`
3. `renderSummary()` / `renderFullPage()` → HTML
4. `renderTurnHistory()` (called inside render, not a separate stage)

The ZIP download already saves all intermediate artifacts (`raw_data.json`, `game_log.json`, `game_state.json`, `summary.html`), so any segment can be re-run from saved inputs.

## Proposed usage

```
npx tsx scripts/run_pipeline.ts game-log raw_data.json         → game_log.json
npx tsx scripts/run_pipeline.ts game-state game_log.json       → game_state.json
npx tsx scripts/run_pipeline.ts game-state raw_data.json       → game_state.json (runs game-log internally first)
npx tsx scripts/run_pipeline.ts render game_state.json         → summary.html (needs game_log.json in same dir)
npx tsx scripts/run_pipeline.ts all raw_data.json              → all three outputs
```

Output files written to the same directory as the input file. ZIP extraction is the caller's responsibility.

## Stages and dependencies

| Stage | Input file(s) | Output file | Extra deps |
|-------|--------------|-------------|------------|
| `game-log` | `raw_data.json` | `game_log.json` | None |
| `game-state` | `raw_data.json` OR `game_log.json` | `game_state.json` | CardDatabase from assets |
| `render` | `game_state.json` + `game_log.json` (same dir) | `summary.html` | CardDatabase, CSS from `sidepanel.css` |
| `all` | `raw_data.json` | all three | All of the above |

### Render stage details

`renderFullPage` needs: `gameState`, `cardDb`, `perspective`, `players`, `tableId`, `css`, `options`.
- `gameState` comes from `game_state.json` via `fromJSON(data, cardDb, players, perspective)`
- `players`, `perspective`, `expansions`, `actions` come from `game_log.json`
- `css` read from `src/sidepanel/sidepanel.css` on disk
- `tableId` extracted from filename or defaulted

### Innovation `SerializedGameState` does NOT include players/perspective/expansions — those live in `GameLog`. So the render stage always needs both files.

### Azul render is simpler — `renderAzulFullPage(state, tableId, css)` only needs the state and CSS.

## Open questions

### Game detection
- `raw_data.json` (`RawExtractionData`) doesn't include game name
- `game_log.json` can be auto-detected (Innovation has `expansions`/`myHand`, Azul has tile-specific fields)
- Options: (a) require `--game` flag for raw_data input, (b) add gameName to raw data format
- Leaning toward `--game` flag for raw_data, auto-detect for game_log/game_state

### Multi-game support
- Both Innovation and Azul pipelines should be supported from the start
- Azul is simpler (no CardDatabase, no perspective, no constraint propagation)

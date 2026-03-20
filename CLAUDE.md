Never prepend `cd` to commands — the working directory is already the project root.
Always use relative paths to project files/folders — never absolute paths (Windows `D:/...` or Unix `/d/...` style).

Always ask clarifying questions before implementing if anything is ambiguous or unclear.

Exclude `node_modules/` from all file and content search patterns — it clogs results with false positives.

Do not inline Python scripts into Bash commands via `python -c`. Instead, write the script to a temporary file (e.g. `tmp/script.py`), execute it with `python tmp/script.py`, then delete it.

## TypeScript Conventions

This is a TypeScript Chrome extension project. Build with Vite, test with vitest.

Use explicit type annotations on function parameters and return values. Use modern union syntax (`string | null`) — not utility types where a union suffices.

Do not break long single-expression lines (template literals, chained calls, etc.) into multiple lines for formatting. Keep them on one line.

Avoid cryptic abbreviations in variable and attribute names. Use descriptive names (`playerPattern` not `pp`, `cardIndex` not `ci`).

Do not add defensive fallbacks that mask invalid data (e.g. `?? "?"`, `?? 0`). Trust that inputs are correct and let invalid values surface naturally — a visible `null` in output or a runtime error is better than silently producing plausible-looking wrong output.

Do not add logic, data structures, classes, or exports to production code that exist only to support tests. Tests should exercise the public API and real behavior — not rely on test-only hooks, flags, exports, or types in production modules.

## Workflow

Run `npm run build` after each batch of changes so the extension can be reloaded and tested in the browser.

Keep the relevant page in `docs/pages/` up to date when code changes affect features, setup, or architecture. The `README.md` only needs updating for changes to the supported game list or project description. The per-game descriptions in `README.md` must be exact copies of the first paragraph from the corresponding `docs/pages/` game page — when one changes, update the other to match. The "Standard features" section must be identical across all game pages — when one changes, update all others to match.

Keep `docs/pages/data-flow.md` up to date when code changes affect data flow, message protocols, or control flow logic. Use the `/document-data-flow` skill.

Any plan that changes or can change logic should include `docs/pages/` and `docs/pages/data-flow.md` updates.

## Commands

- `npm run build` — build the extension to dist/
- `npm test` — run all tests
- `npm run lint` — TypeScript type checking (`tsc --noEmit`)
- `npm run dev` — watch mode build
- `npm run game-log -- <raw_data.json> [--game <name>]` — process raw data into game log
- `npm run game-state -- <game_log.json> [--debug] [--game <name>]` — process game log into game state (--debug writes per-entry snapshots to game_states/)

## Project Structure

- `src/models/types.ts` — shared BGA types (GameName, RawPacket, RawExtractionData, cardIndex) + re-exports Innovation types
- `src/games/innovation/types.ts` — Innovation types (Card, CardInfo, CardDatabase, enums, actions, log entries)
- `src/games/innovation/process_log.ts` — Innovation BGA packet processing
- `src/games/innovation/game_state.ts` — GameState interface (zone data), createGameState(), cardsAt()
- `src/games/innovation/game_engine.ts` — GameEngine class (state tracking + constraint propagation), extractSuspects()
- `src/games/innovation/serialization.ts` — toJSON/fromJSON serialization, SerializedGameState type
- `src/games/innovation/turn_history.ts` — Turn action types (TurnAction, ActionDetail, ActionType) and recent-turns grouping
- `src/games/innovation/render.ts` — Innovation HTML summary renderer
- `src/games/innovation/config.ts` — Innovation section layout configuration
- `src/games/azul/process_log.ts` — Azul BGA packet processing
- `src/games/azul/game_state.ts` — Azul bag/discard/wall tracking
- `src/games/azul/render.ts` — Azul tile count table renderer
- `src/games/crew/types.ts` — Crew types (suit constants, ALL_SUITS, CrewCard, card key helper, SUIT_VALUES)
- `src/games/crew/process_log.ts` — Crew BGA packet processing (missions, tricks, communications)
- `src/games/crew/game_state.ts` — CardGuess candidate model, Trick interface, CrewGameState interface, createCrewGameState() factory
- `src/games/crew/game_engine.ts` — processCrewState() pipeline entry, CardGuess candidate narrowing, constraint propagation, getPlayedCards(), playerSuitStatus()
- `src/games/crew/serialization.ts` — toJSON/fromJSON serialization for Crew game state
- `src/games/crew/render.ts` — Crew HTML renderer (card grid, suit matrix, trick history)
- `src/games/crew/styles.css` — Crew-specific CSS styles
- `src/render/help.ts` — help page content (shared)
- `src/render/icons.ts` — shared icon utilities
- `src/render/toggle.ts` — shared toggle/tooltip logic (side panel + ZIP export)
- `src/extract.ts` — content script (MAIN world)
- `src/pipeline.ts` — pure pipeline logic (processGameLog, processGameState, runPipeline) shared by background.ts and CLI scripts
- `src/background.ts` — service worker (orchestration, side panel management, live tracking)
- `scripts/game-log.ts` — CLI: raw_data.json → game_log.json
- `scripts/game-state.ts` — CLI: game_log.json → game_state.json (+ --debug snapshots)
- `sidepanel.html` — side panel HTML entry point (project root, Vite input)
- `src/sidepanel/` — side panel UI (game-type-aware rendering dispatch)
- `assets/bga/innovation/` — Innovation game data (card_info.json, cards/, icons/, sprites/)
- `assets/bga/azul/tiles/` — Azul tile color PNGs
- `assets/extension/` — extension icons
- `docs/pages/data-flow.md` — data flow architecture, message protocols, connection management

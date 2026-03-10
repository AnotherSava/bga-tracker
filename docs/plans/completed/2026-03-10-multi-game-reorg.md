# Reorganize Project for Multi-Game Support

## Summary

Moved game-specific code into `src/games/` and split Innovation types from shared BGA types.

## Changes

### Task 1: Move game folders to `src/games/`
- `src/innovation/` → `src/games/innovation/`
- `src/azul/` → `src/games/azul/`
- Updated imports in background.ts, sidepanel.ts, and all test files

### Task 2: Split `src/models/types.ts`
- Created `src/games/innovation/types.ts` with Innovation-specific types (Card, CardDatabase, enums, actions, log entries)
- Trimmed `src/models/types.ts` to shared types (GameName, RawPacket, RawExtractionData, cardIndex)
- Added re-export from models/types.ts for backward compatibility
- Innovation modules import from local `./types.js`

### Task 3: Colocate game tests
- `src/__tests__/game_state.test.ts` → `src/games/innovation/__tests__/game_state.test.ts`
- `src/__tests__/process_log.test.ts` → `src/games/innovation/__tests__/process_log.test.ts`
- `src/__tests__/azul_game_state.test.ts` → `src/games/azul/__tests__/game_state.test.ts`
- `src/__tests__/azul_process_log.test.ts` → `src/games/azul/__tests__/process_log.test.ts`
- `src/__tests__/azul_render.test.ts` → `src/games/azul/__tests__/render.test.ts`

### Task 4: Update documentation
- Updated CLAUDE.md Project Structure section

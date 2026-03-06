Never prepend `cd` to commands — the working directory is already the project root.
Always use relative paths to project files/folders — never absolute paths (Windows `D:/...` or Unix `/d/...` style).

Always ask clarifying questions before implementing if anything is ambiguous or unclear.

## TypeScript Conventions

This is a TypeScript Chrome extension project. Build with Vite, test with vitest.

Use explicit type annotations on function parameters and return values. Use modern union syntax (`string | null`) — not utility types where a union suffices.

Do not break long single-expression lines (template literals, chained calls, etc.) into multiple lines for formatting. Keep them on one line.

Avoid cryptic abbreviations in variable and attribute names. Use descriptive names (`playerPattern` not `pp`, `cardIndex` not `ci`).

## Workflow

Run `npm run build` after each batch of changes so the extension can be reloaded and tested in the browser.

## Commands

- `npm run build` — build the extension to dist/
- `npm test` — run all tests
- `npm run lint` — TypeScript type checking (`tsc --noEmit`)
- `npm run dev` — watch mode build

## Project Structure

- `src/models/types.ts` — core types (Card, CardInfo, CardDatabase, enums)
- `src/engine/process_log.ts` — BGA packet processing
- `src/engine/game_state.ts` — unified game state engine
- `src/render/summary.ts` — HTML summary renderer
- `src/render/config.ts` — section layout configuration
- `src/extract.ts` — content script (MAIN world)
- `src/background.ts` — service worker
- `sidepanel.html` — side panel HTML entry point (project root, Vite input)
- `src/sidepanel/` — side panel UI
- `assets/card_info.json` — card database

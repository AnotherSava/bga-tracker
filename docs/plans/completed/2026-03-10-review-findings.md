# Address Frontend Review Findings

## Overview

Address actionable findings from a frontend code review of the Chrome extension.
Covers code quality improvements (comments, fail-fast, type safety), shared logic
extraction, message flow simplification (unified extraction, eliminated round trips),
and live tracking reliability fixes.

## Context

- Files involved:
  - Modify: `src/background.ts` — message flow, classifyNavigation, rate limiter
  - Modify: `src/sidepanel/sidepanel.ts` — message handling, rendering dispatch
  - Modify: `src/games/innovation/render.ts` — comments, isCardResolved, SUMMARY_JS extraction
  - Modify: `src/games/innovation/game_state.ts` — fail-fast on cardsAt and friends
  - Modify: `src/games/azul/game_state.ts` — TileCounts tuple type
  - Modify: `src/extract.ts` — explanatory comment
  - Modify: `manifest.json` — remove unused web_accessible_resources
  - Create: `src/render/toggle.ts` — shared toggle/tooltip logic
  - Create: `src/__tests__/fixtures/` — committed test fixture data
- Related patterns: existing extraction pipeline, port-based side panel lifecycle
- Dependencies: none
- Related plan: `docs/plans/draft/2026-03-11-gamestate-restructuring.md` (deferred GameState
  restructuring and PipelineResults discriminated union)

## Development Approach

- Testing approach: Regular (code first, then tests)
- Complete each task fully before moving to the next
- **CRITICAL: every task MUST include new/updated tests**
- **CRITICAL: all tests must pass before starting next task**

## Design Notes

**Task grouping:** Items fall into four independent groups:
1. Quick fixes (comments, types, manifest cleanup) — no dependencies
2. Shared logic extraction — standalone refactor
3. Message flow simplification — ordered chain: remove "skip" → unify flows → eliminate
   Side Panel Show → send results with notification → verify cached results fix
4. Live tracking fixes — rate limiter deferred re-extraction

**Message flow ordering rationale:** Removing "skip" (Task 4) simplifies navigation
logic first. Unifying flows (Task 5) eliminates the supported/unsupported branching
and the `"getRawData"` message. Eliminating the Side Panel Show flow (Task 6) removes
the `"getResults"` round trip by re-sending results on port connect. Sending results
directly with the notification (Task 7) removes the remaining `"resultsReady"` →
`"getResults"` round trip. After these changes, irrelevant cached results (Task 8)
should be mostly fixed — verify and clean up any remaining issues.

**Shared toggle/tooltip extraction:** The side panel imports the shared functions
directly (wrapping with localStorage persistence). For the ZIP download's `SUMMARY_JS`,
the same functions are serialized into a plain JS string via `.toString()`. This ensures
a single source of truth while supporting both contexts.

**Rate limiter fix:** When a mutation is dropped within the 5s window, schedule a
deferred re-extraction after the remaining time (e.g. 3s elapsed → fire in 2s). This
respects the minimum interval while ensuring the latest state is always picked up.

**Fail-fast principle:** Internal APIs should throw on invalid input rather than
returning plausible but incorrect defaults. The `?? []` fallback in `cardsAt()` masks
bugs; a thrown error surfaces them immediately. Only validate gracefully at system
boundaries (user input, external APIs).

## Review findings reference

1. Module-level mutable state in `render.ts` → **Task 1**
2. Duplicated JS logic (sidepanel.ts / SUMMARY_JS) → **Task 3**
3. `PipelineResults` uses `any` → **separate plan**
4. `isCardResolved` linear scan → **Task 2**
5. `TileCounts` typed as `number[]` → **Task 1**
6. `cardsAt` non-null assertions → **Task 2**
7. Gitignored fixture test → **Task 2**
8. `sidepanel.ts` size — will shrink from Tasks 3 and 5
9. Inconsistent `getElementById` null guards — covered by Task 2
10. `extractGameData` resolves with error objects → **Task 1**
11. `web_accessible_resources` glob → **Task 1**
12. `!important` in CSS — justified, skip
13. `sidepanel.html` at root — standard Vite pattern, skip
14. Accessibility — personal-use extension, skip
15. No `return true` in `onMessage` — preventive only, skip

## Implementation Steps

### Task 1: Quick fixes (comments, types, manifest)

**Files:**
- Modify: `src/games/innovation/render.ts` — comment on `useTextTooltips` (line 22)
- Modify: `src/extract.ts` — comment on error-object pattern (lines 18-19)
- Modify: `src/games/azul/game_state.ts` — TileCounts tuple type (line 13)
- Modify: `manifest.json` — remove `web_accessible_resources` (lines 34-39)

- [x] Add comment at `useTextTooltips` declaration explaining module-level state is
      intentional (single-threaded extension, simpler than threading through render functions)
- [x] Add comment at `extractGameData()` error returns explaining why it resolves with
      `{ error, msg }` instead of rejecting (Chrome executeScript wraps rejections in
      generic errors, losing the message)
- [x] Change `type TileCounts = number[]` to
      `type TileCounts = [number, number, number, number, number, number]`
- [x] Remove the `web_accessible_resources` section from `manifest.json` (all asset
      access is from extension contexts which don't need it)
- [x] Fix any type errors from TileCounts change (e.g. `zeroCounts()` return type)
- [x] Run `npm run lint` — must pass
- [x] Run `npm test` — must pass before next task

### Task 2: Fail-fast audit and isCardResolved optimization

**Files:**
- Modify: `src/games/innovation/game_state.ts` — replace `?? []` with throws in `cardsAt()`
- Modify: `src/games/innovation/render.ts` — replace `isCardResolved` with Set lookup
- Modify: `src/__tests__/background.test.ts` — move Azul fixture to committed location
- Create: `src/__tests__/fixtures/azul_816402832.json` — committed Azul fixture
- Create: `src/__tests__/fixtures/innovation_sample.json` — committed Innovation fixture

- [x] In `cardsAt()` (line 113): replace `?? []` fallbacks with explicit throws when
      the zone/player combination is invalid (e.g. `player` is null for `"hand"` zone)
- [x] Audit other `?? []` patterns in `game_state.ts` — distinguish between legitimate
      defaults (e.g. `fromJSON` loading optional fields) and silent error masking
- [x] In `prepareAllCards()`: build a `Set<string>` of all resolved card names by
      scanning zones once, then use `set.has(indexName)` instead of `isCardResolved()`
- [x] Remove `isCardResolved()` function
- [x] Create committed fixture files under `src/__tests__/fixtures/` with minimal
      `raw_data.json` samples for both Azul and Innovation
- [x] Update the Azul fixture test in `background.test.ts` to use committed fixture
- [x] Add an Innovation end-to-end pipeline test using committed fixture
- [x] Write tests for `cardsAt()` throwing on invalid input
- [x] Run `npm test` — must pass before next task

### Task 3: Extract shared toggle/tooltip logic

**Files:**
- Create: `src/render/toggle.ts` — shared pure DOM functions
- Modify: `src/sidepanel/sidepanel.ts` — import from shared module
- Modify: `src/games/innovation/render.ts` — generate SUMMARY_JS from shared functions
- Create: `src/render/__tests__/toggle.test.ts`

- [x] Create `src/render/toggle.ts` with two pure functions:
      - `positionTooltip(tip, mouseX, mouseY)` — tooltip placement math
      - `applyToggleMode(toggle, mode, targetId)` — the mode-application switch
- [x] Update `src/sidepanel/sidepanel.ts` to import and use shared functions (keeping
      localStorage persistence wrapper on top)
- [x] Update `SUMMARY_JS` in `render.ts` to serialize the shared functions via
      `.toString()` instead of maintaining a separate copy
- [x] Write tests for `positionTooltip` and `applyToggleMode`
- [x] Verify ZIP download still works (SUMMARY_JS generates valid standalone JS)
- [x] Run `npm test` — must pass before next task

### Task 4: Remove "skip" classification

**Files:**
- Modify: `src/background.ts` — remove "skip" from `classifyNavigation()` and `NavigationAction`
- Modify: `src/__tests__/background.test.ts` — remove/update skip tests

- [x] Remove the `{ action: "skip" }` variant from `NavigationAction` type (line 38)
- [x] Remove the `"skip"` branch from `classifyNavigation()` (lines 383-384)
- [x] Remove the `currentTableNumber` parameter from `classifyNavigation()` if no
      longer needed
- [x] Update `handleNavigation()` to remove skip handling
- [x] Update tests: remove skip-related assertions, add test that same-table navigation
      triggers re-extraction
- [x] Run `npm test` — must pass before next task

### Task 5: Unify supported and unsupported game extraction flows

**Files:**
- Modify: `src/background.ts` — merge extraction branches, remove `"getRawData"` handler
- Modify: `src/sidepanel/sidepanel.ts` — remove `"getRawData"` handling, unify render path
- Modify: `src/__tests__/background.test.ts`

- [x] Make `PipelineResults.gameLog` and `PipelineResults.gameState` nullable
- [x] For unsupported games: populate `PipelineResults` with `rawData` only (gameLog
      and gameState null), send `"resultsReady"` instead of `"notAGame"`
- [x] Remove `lastRawData` variable and `"getRawData"` message handler from background
- [x] Update side panel render logic: if `gameState` present → render game page; if
      only `rawData` → help page with download enabled; if null → help page
- [x] Remove `"getRawData"` request from side panel
- [x] Keep `"notAGame"` only for non-BGA pages (no extraction at all)
- [x] Update tests for the unified flow
- [x] Run `npm test` — must pass before next task

### Task 6: Eliminate Side Panel Show flow

**Files:**
- Modify: `src/background.ts` — re-send results in onConnect handler
- Modify: `src/sidepanel/sidepanel.ts` — remove on-load `"getResults"` request
- Modify: `src/__tests__/background.test.ts`

- [x] In the `onConnect` handler: if `lastResults` is cached, immediately send
      `"resultsReady"` (or the results directly, depending on Task 7 ordering) on the
      newly connected port
- [x] Remove the on-load `"getResults"` request from side panel (lines 787-796)
- [x] Side panel starts in loading/help state by default, waits for push from background
- [x] Update tests for the new connect behavior
- [x] Run `npm test` — must pass before next task

### Task 7: Send PipelineResults directly with notification

**Files:**
- Modify: `src/background.ts` — include results in message payload
- Modify: `src/sidepanel/sidepanel.ts` — read results from message instead of requesting
- Modify: `src/__tests__/background.test.ts`

- [x] Change `"resultsReady"` message to include the `PipelineResults` payload directly
- [x] Remove the `"getResults"` message handler from background
- [x] Update side panel to read results from the notification message
- [x] Update the onConnect handler (Task 6) to send results in the same format
- [x] Remove `"getResults"` from the message protocol
- [x] Update tests for the new message format
- [x] Run `npm test` — must pass before next task

### Task 8: Verify cached results fix

**Files:**
- Modify: `src/sidepanel/sidepanel.ts` — verify no stale/irrelevant results shown

- [x] Verify that after Tasks 5-7, the side panel never shows results from a different
      table (the push-only model ensures results are always fresh)
- [x] If any edge cases remain (e.g. background restart), add validation that results
      match the current context before rendering
- [x] Run `npm test` — must pass before next task

### Task 9: Fix stale state from rate limiter

**Files:**
- Modify: `src/background.ts` — add deferred re-extraction on rate limit drop
- Modify: `src/__tests__/background.test.ts`

- [x] When a `"gameLogChanged"` message is dropped by the rate limiter, schedule a
      `setTimeout` to re-extract after the remaining time in the 5s window
      (e.g. `LIVE_MIN_INTERVAL_MS - (Date.now() - lastExtractionTime)`)
- [x] Clear any pending deferred timer when a new extraction starts or live tracking stops
- [x] Write tests: mutation dropped at 3s triggers extraction at 5s, pending timer
      cleared on new extraction, pending timer cleared on stop
- [x] Run `npm test` — must pass before next task

### Task 10: Verify acceptance criteria

- [x] Manual test: open side panel on a supported game table, verify rendering
- [x] Manual test: open side panel on an unsupported game table, verify help page with download
- [x] Manual test: switch to a non-BGA tab, verify help page without download
- [x] Manual test: close and reopen side panel on same table, verify fresh results (no stale data)
- [x] Manual test: switch between two different game tables, verify correct results each time
- [x] Manual test: verify live tracking updates without stale state after rate-limited mutations
- [x] Manual test: verify ZIP download works for both supported and unsupported games
- [x] Run full test suite: `npm test`
- [x] Run linter: `npm run lint`

### Task 11: Update documentation

- [x] Update `docs/data-flow.md` to reflect new message protocol (run `/document-data-flow`)
- [x] Update CLAUDE.md if internal patterns changed
- [x] Move this plan to `docs/plans/completed/`

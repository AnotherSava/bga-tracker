# Formalize ExtractionSource enum

## Overview

Replace ad-hoc source string literals in `background.ts` with a typed `ExtractionSource` union and a `shouldShowLoading()` helper, so behavioral decisions (show loading, set badge, etc.) are driven by the source enum rather than scattered negation checks like `source !== "reconnect"`.

## Context

- Files involved:
  - Modify: `src/background.ts` — add type, helper, update signature and call sites
  - Modify: `src/__tests__/background.test.ts` — add tests for `shouldShowLoading`
  - Modify: `docs/data-flow.md` — reference new helper in shutdown cycle docs
- Related patterns: `NavigationAction` type union in `background.ts`; `PinMode` type union with `VALID_PIN_MODES` set
- Dependencies: None

## Development Approach

- Testing approach: Regular (code first, then tests)
- Complete each task fully before moving to the next
- **CRITICAL: every task MUST include new/updated tests**
- **CRITICAL: all tests must pass before starting next task**

## Design Notes

**Why a string union, not a const enum**: TypeScript string union types (`"click" | "navigation" | ...`) are idiomatic for this codebase — see `PinMode` and `NavigationAction`. They erase at runtime, produce no extra JS, and work naturally with `===` checks.

**`shouldShowLoading` as a positive check**: Currently the loading guard is `source !== "reconnect"` — a negation that must be mentally inverted. The helper uses positive semantics: `shouldShowLoading("click")` returns `true`. This makes the behavioral contract self-documenting and easier to extend if new sources are added.

**`stopLiveTracking` reason stays `string`**: The `reason` parameter in `stopLiveTracking(reason: string)` is a free-form debug log string (e.g. `"click: unsupported game"`, `"auto-close"`), not an extraction source. No change needed.

**`triggerLiveExtraction` is not a call site**: Live re-extraction bypasses `resolveContent` and calls `extractFromTab` directly. The `"live"` value exists in the enum for `shouldShowLoading` coverage but no call site passes it to `resolveContent`.

**Call site mapping**:
- `togglePanel` (line 622/628): `"click"` — unchanged
- `handleNavigation` (line 683): `"nav"` -> `"navigation"`
- `onConnect` reconnect (line 570): `"reconnect"` — unchanged

## Implementation Steps

### Task 1: Add ExtractionSource type and shouldShowLoading helper

**Files:**
- Modify: `src/background.ts`
- Modify: `src/__tests__/background.test.ts`

- [x] Add after `PipelineResults` interface (~line 35):
  ```typescript
  export type ExtractionSource = "click" | "navigation" | "reconnect" | "live";

  export function shouldShowLoading(source: ExtractionSource): boolean {
    return source === "click" || source === "navigation";
  }
  ```
- [x] Update `resolveContent` signature: `source: string` -> `source: ExtractionSource`
- [x] Replace loading guard (line 524):
  - Before: `if (source !== "reconnect") chrome.runtime.sendMessage(...)`
  - After: `if (shouldShowLoading(source)) chrome.runtime.sendMessage(...)`
- [x] Update call site at `handleNavigation` (line 683): `"nav"` -> `"navigation"`
- [x] Update error handler reason (line 687): `"nav: error"` -> `"navigation: error"`
- [x] Add tests for `shouldShowLoading` in `src/__tests__/background.test.ts`:
  - `click` -> true, `navigation` -> true, `reconnect` -> false, `live` -> false
- [x] Run `npm test` — all tests pass
- [x] Run `npm run lint` — type-check passes

### Task 2: Update documentation

**Files:**
- Modify: `docs/data-flow.md`

- [x] In "Service worker shutdown cycle" section, replace reference to `source !== "reconnect"` with `shouldShowLoading()`

### Task 3: Verify acceptance criteria

- [x] Run full test suite: `npm test`
- [x] Run linter: `npm run lint`
- [x] Run build: `npm run build`
- [x] Move this plan to `docs/plans/completed/`

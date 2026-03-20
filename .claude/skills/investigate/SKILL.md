---
name: investigate
description: Debug a game state discrepancy reported by the user. Extracts archive, analyzes all pipeline stages, creates a failing regression test with correct expectations, fixes the logic, and verifies the fix.
argument-hint: [archive-or-table-id] <description-of-discrepancy>
allowed-tools: Bash(unzip *), Bash(ls *), Bash(mkdir *), Bash(npm test*), Bash(npm run test*), Bash(npm run build*), Bash(npm run lint*), Read, Write, Edit, Glob, Grep, Agent
---

# Debug Game State Discrepancy

Investigate a user-reported discrepancy in any supported game's tracker output, create a regression test, and fix the bug.

Supported games and their pipeline files are listed in `CLAUDE.md` under Project Structure. Data flow between components is documented in `docs/pages/data-flow.md`.

## Input

`$ARGUMENTS` should contain:
1. **(Optional)** An archive filename (e.g. `bgaa_816598364.zip`) or just a table ID (e.g. `816598364`). If a bare table ID is given, the archive is `data/bgaa_<TABLE_ID>.zip`. If neither is provided, use the most recently created `.zip` file in `data/` (find it with `ls -t data/*.zip | head -1`).
2. A description of the discrepancy the user noticed

If the discrepancy description is missing, ask the user.

## Workflow

### Step 1: Extract archive

Resolve the archive path from the argument (filename or table ID), or use the most recently created `.zip` in `data/` if not specified. Derive the folder name by stripping `.zip` (e.g. `bgaa_816598364`).

```
mkdir -p data/<FOLDER>
unzip -o data/<ARCHIVE> -d data/<FOLDER>
```

The archive contains up to 4 files:
- `raw_data.json` — raw BGA packet extraction (input to the game's `process_log`)
- `game_log.json` — structured game log (output of `process_log`, input to game engine)
- `game_state.json` — serialized game state (output of serialization)
- `summary.html` — rendered HTML summary

If only `raw_data.json` is present, the pipeline failed before producing the other files — the raw data is the starting point for investigation.

### Step 2: Identify the game

Determine which game this data belongs to. Check `raw_data.json` for clues:
- Look at the BGA notification types in the packets (e.g. `transferedCard` → Innovation, `factoriesFilled` → Azul, `newHand`/`playCard` → Crew)
- Or check the archive name against known table IDs

Once identified, consult `CLAUDE.md` Project Structure for the relevant pipeline files (`process_log.ts`, `game_state.ts`/`game_engine.ts`, `serialization.ts`, `render.ts`).

### Step 3: Analyze the discrepancy

Read the relevant files from `data/<FOLDER>/` to understand the reported issue. Work backwards from the symptom:

1. **summary.html** — confirm the user's observation visually (search for the specific cards/sections mentioned)
2. **game_state.json** — check the serialized state for the problematic data
3. **game_log.json** — trace the entries that led to the bad state
4. **raw_data.json** — if the game_log looks wrong, check whether `process_log` misinterpreted raw BGA packets

Identify which pipeline stage introduced the error:
- **raw_data.json is wrong** → extraction bug in `src/extract.ts`
- **game_log.json is wrong** → bug in the game's `process_log.ts`
- **game_state.json is wrong but game_log is correct** → bug in the game's engine (`game_state.ts` or `game_engine.ts`)
- **summary.html is wrong but game_state is correct** → rendering bug in the game's `render.ts`

See `docs/pages/data-flow.md` for the full pipeline flow and serialization boundaries.

Document your findings clearly before proceeding.

### Step 4: Determine the correct expected output

Based on your analysis:
- Determine what the **correct** output should be at the buggy stage
- Be specific — identify exact values, zones, players, and states involved

### Step 5: Create a regression test

Create or extend a test in the game's `__tests__/` directory that:
1. Loads the relevant input data from the archive (read it from `data/<FOLDER>/`)
2. Runs the buggy pipeline stage
3. Asserts the **correct** expected output (not the current buggy output)

**Test data strategy:**
- For small reproducers: inline the minimal log entries needed to trigger the bug
- For complex bugs requiring full game context: load the fixture JSON and run the full pipeline, then assert the specific problematic part of the output

When loading fixture data, use the pattern:
```typescript
import { readFileSync } from "fs";
import { resolve, dirname } from "path";
import { fileURLToPath } from "url";

const thisDir = dirname(fileURLToPath(import.meta.url));
const fixture = JSON.parse(readFileSync(resolve(thisDir, "../../data/<FOLDER>/game_log.json"), "utf-8"));
```

Name the test descriptively based on the bug.

### Step 6: Verify the test fails

```
npm test
```

Confirm that the new test fails with an assertion error that matches the known buggy behavior. If the test passes, the test is not correctly capturing the bug — revisit Step 5.

### Step 7: Fix the bug

Modify the source code to fix the bug. Keep changes minimal and focused on the specific bug.

For extraction bugs (`src/extract.ts`): after fixing, ask the user to reload the extension and re-download the data.

### Step 8: Verify the fix

```
npm test
npm run build
```

All tests must pass — both the new regression test and all existing tests.

### Step 9: Report

Summarize:
1. **Root cause** — what went wrong and where
2. **Fix** — what was changed
3. **Test** — what the regression test covers
4. **Verification** — test and build results

---
name: innovation
description: Extract and track Innovation game state from a BGA table. Use when the user wants to analyze an Innovation game, fetch game history, or track card state.
argument-hint: <table-url>
allowed-tools: Bash(python *), Bash(ls *), Read, Write, Glob
---

# Innovation Game Tracker

Extract game log from BGA and track card state for an Innovation table.

## Input

`$ARGUMENTS` should be a BGA table URL like `https://boardgamearena.com/<N>/innovation/innovation?table=<TABLE_ID>`.

If no argument is provided, ask the user for the table URL.

Extract the TABLE_ID from the `?table=` query parameter.

## Prerequisites

browse.py must be running. Verify by writing `url` to `scripts/cmd.txt` and waiting for `cmd.txt` to be deleted (browse.py deletes it on read). Do NOT trust `output/result.txt` alone — it may contain stale content from a previous session.

If cmd.txt is not consumed after a few seconds, browse.py is not running. Start it:
```
venv/Scripts/python -m browser.browse &
```

Wait a few seconds, then verify it's ready by writing `url` to `scripts/cmd.txt` and confirming cmd.txt gets consumed and result.txt is updated.

**Important**: Never write real commands to `scripts/cmd.txt` before browse.py is confirmed running — commands written before startup may be consumed during initialization without producing a result.

**If browse.py fails to start** with `TargetClosedError` or Chrome exit code 21, another instance is likely already running and holding the Chrome profile lock. Check for existing python processes before trying to restart.

## Workflow

All browse.py communication is file-based:
- Write a command to `scripts/cmd.txt`
- Wait for `output/result.txt` to appear (poll until it exists and has content)
- Read the result
- Delete `scripts/cmd.txt` if it still exists before sending the next command

**Important**: After writing each command, wait and poll for the result file to be updated. browse.py deletes `cmd.txt` when it reads it, so wait until `cmd.txt` is gone and `result.txt` has new content.

**Error handling**: After EVERY command, check the result for errors (strings starting with `Error:` or containing `{"error"`). If a command fails, report the exact error to the user and stop — do not guess at the cause or try to continue.

### Step 1: Navigate to the table

Write to `scripts/cmd.txt`:
```
goto $ARGUMENTS
```

Read `output/result.txt`. It should say `Navigated to: <url>`. If it contains an error, report it and stop.

### Step 2: Check login status

**This step is mandatory** — BGA shows game content even to logged-out users, but the API calls in later steps will fail without login.

Write to `scripts/cmd.txt`:
```
eval document.body.innerText.includes('You are a spectator')
```

If the result is `True`, the user is not logged in (shown as spectator). In that case:
1. Tell the user: "You're not logged in to BGA. Please log in in the browser window, then let me know."
2. Ask them to confirm once they've logged in (use AskUserQuestion).
3. After confirmation, re-navigate to the table URL (repeat Step 1) and re-check login.

### Step 3: Fetch notification history

Write to `scripts/cmd.txt`:
```
eval scripts/fetch_full_history.js
```

Read the result — it should be JSON with `players` and `packets`. If it shows an error, report it and stop.

### Step 4: Save raw log and determine opponent

Save the JSON result to a temporary location first, then determine the correct directory name.

1. Create `data/<TABLE_ID>/` if it doesn't exist.
2. Save the JSON result to `data/<TABLE_ID>/raw_log.json`.
3. Run process_log to get player names:
```
python -m bga_tracker.innovation.process_log data/<TABLE_ID>/raw_log.json data/<TABLE_ID>/game_log.json
```
4. Read the `players` field from `data/<TABLE_ID>/game_log.json` to identify the opponent — the player whose name is NOT `PLAYER_NAME` from `.env` (currently `AnotherSava`).
5. Rename the directory to `data/<TABLE_ID> <opponent>/`:
```
mv "data/<TABLE_ID>" "data/<TABLE_ID> <opponent>"
```

The `<TABLE_ID> <opponent>` directory format is required by track_state.py and format_state.py.

### Step 5: Track card state

Run:
```
python -m bga_tracker.innovation.track_state <TABLE_ID>
```

This produces `data/<TABLE_ID> <opponent>/game_state.json` — structured game state with card objects.

### Step 6: Format summary

Run:
```
python -m bga_tracker.innovation.format_state <TABLE_ID>
```

This runs the tracker internally (no dependency on game_state.json) and produces `data/<TABLE_ID> <opponent>/summary.html` — a colored HTML summary of hidden information from both perspectives.

Report the output path to the user. Do NOT generate ad-hoc summaries, read game_state.json, or write scripts to inspect the data — the HTML file is the final output.

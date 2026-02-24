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

browse.py must be running. Check by writing a `url` command to `scripts/cmd.txt` and waiting for a response in `output/result.txt`.

If it's not running (no response after a few seconds), start it in the background:
```
venv/Scripts/python scripts/browse.py &
```

Wait a few seconds for the browser to initialize before proceeding.

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

Read the result — it should contain JSON with `total_chars` and `data_entries`. If it shows an error, report it and stop.

### Step 4: Extract game log

Write to `scripts/cmd.txt`:
```
eval scripts/innovation/extract_log.js
```

Read the result — it should be JSON with `total_entries` and a `log` array. This is the game log data.

### Step 5: Save game log

Create the directory `data/<TABLE_ID>/` if it doesn't exist.

Save the extracted JSON result to `data/<TABLE_ID>/game_log.json`.

### Step 6: Track card state

Run:
```
python scripts/innovation/track_state.py <TABLE_ID>
```

This produces `data/<TABLE_ID>/game_state.json` — structured game state with card objects.

### Step 7: Report results

Read `data/<TABLE_ID>/game_state.json` and present a summary to the user showing:
- Player names and their board/hand/score card counts
- Total cards in deck
- Any warnings from track_state.py output

### Step 8: Format summary

Run:
```
python scripts/innovation/format_state.py <TABLE_ID>
```

This produces `data/<TABLE_ID>/summary.html` — a colored HTML summary of hidden information from both perspectives.

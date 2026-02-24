---
name: test
description: Run regression tests for the Innovation tracker pipeline.
allowed-tools: Bash(python *), Bash(venv/Scripts/python *), Read, Glob, Grep
---

# Run Regression Tests

Run the test suite and report results.

## Workflow

### Step 1: Run tests

```
venv/Scripts/python -m pytest tests/ -v
```

### Step 2: Report results

If all tests pass, report success with a short summary.

If any tests fail, analyze the failure:
1. Read the pytest output carefully — note which test(s) failed and the assertion diff
2. Read the relevant reference file and compare with the actual output
3. Explain **what** changed (specific lines/sections that differ) and **why** it likely changed (recent code modifications to track_state.py or format_state.py)
4. Suggest whether the reference fixtures need updating or the code change introduced a bug

#!/bin/bash
# Send a command to browse.py and wait for the result.
# Usage: bash scripts/cmd.sh <command>
# Example: bash scripts/cmd.sh "goto https://boardgamearena.com"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
CMD_FILE="$SCRIPT_DIR/cmd.txt"
RESULT_FILE="$PROJECT_ROOT/output/result.txt"
TIMEOUT=${CMD_TIMEOUT:-30}

if [ -z "$1" ]; then
    echo "Usage: cmd.sh <command>"
    exit 1
fi

rm -f "$RESULT_FILE" 2>/dev/null
echo "$*" > "$CMD_FILE"

for i in $(seq 1 $((TIMEOUT * 2))); do
    if [ ! -f "$CMD_FILE" ] && [ -f "$RESULT_FILE" ]; then
        cat "$RESULT_FILE"
        exit 0
    fi
    sleep 0.5
done

echo "TIMEOUT: browse.py did not respond within ${TIMEOUT}s"
exit 1

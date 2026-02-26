"""Process raw BGA notification packets into a structured game log.

Reads the raw JSON produced by fetch_full_history.js (packets + player names)
and writes structured game_log.json consumed by state_tracker.py.

CLI: python -m bga_tracker.innovation.process_log <input_path> <output_path>
"""

import json
import re
import sys
from pathlib import Path

ICON_MAP = {"1": "crown", "2": "leaf", "3": "lightbulb", "4": "castle", "5": "factory", "6": "clock"}


def expand_template(template: str, args: dict) -> str:
    """Resolve ``${key}`` placeholders in a BGA log template.

    Handles recursive sub-templates (objects with ``log`` + ``args`` keys) and
    named objects (with a ``name`` key).
    """
    if not template:
        return ""

    def replacer(match: re.Match) -> str:
        key = match.group(1)
        val = args.get(key)
        if val is None:
            return ""
        if isinstance(val, dict):
            if "log" in val and "args" in val:
                return re.sub(r"<[^>]+>", "", expand_template(val["log"], val["args"])).strip()
            if "name" in val:
                return val["name"]
            return ""
        return str(val)

    return re.sub(r"\$\{([^}]+)\}", replacer, template)


def clean_html(msg: str) -> str:
    """Convert BGA HTML log markup to plain text.

    Icon spans become ``[name]``, age spans become ``[N]``, all other HTML is
    stripped, and whitespace is collapsed.
    """
    msg = re.sub(r'<span[^>]*icon_(\d)[^>]*></span>', lambda m: "[" + ICON_MAP.get(m.group(1), "icon" + m.group(1)) + "]", msg)
    msg = re.sub(r'<span[^>]*age[^>]*>(\d+)</span>', r'[\1]', msg)
    msg = re.sub(r'<[^>]+>', '', msg)
    return re.sub(r'\s+', ' ', msg).strip()


def normalize_hyphens(text: str) -> str:
    """Replace U+2011 (non-breaking hyphen) with ASCII hyphen."""
    return text.replace("\u2011", "-")


def process_raw_log(raw_data: dict) -> dict:
    """Transform raw BGA packets into structured game log entries.

    Parameters
    ----------
    raw_data:
        Dict with ``players`` (pid→name map) and ``packets`` (list of BGA
        notification packets from ``window.__full_history.data``).

    Returns
    -------
    dict
        ``{players: {pid: name, ...}, log: [entry, ...]}`` where each entry is
        either a transfer (structured fields) or a log message (plain text).
    """
    player_names: dict[str, str] = raw_data.get("players", {})
    packets: list[dict] = raw_data.get("packets", [])
    log: list[dict] = []

    # Pass 1: collect player-view transferedCard args, grouped by move_id.
    player_transfers_by_move: dict[str, list[dict]] = {}
    for packet in packets:
        notifications = packet.get("data") or []
        move_id = str(packet.get("move_id", ""))
        for notif in notifications:
            if notif.get("type") == "transferedCard" and notif.get("args"):
                player_transfers_by_move.setdefault(move_id, []).append(notif["args"])

    # Pass 2: iterate spectator notifications (the canonical ordering).
    transfer_count_by_move: dict[str, int] = {}

    for packet in packets:
        move_id = str(packet.get("move_id", ""))
        time = packet.get("time", 0)
        notifications = packet.get("data") or []

        for notif in notifications:
            notif_type = notif.get("type", "")
            args = notif.get("args") or {}

            if notif_type == "transferedCard_spectator":
                idx = transfer_count_by_move.get(move_id, 0)
                transfer_count_by_move[move_id] = idx + 1
                move_transfers = player_transfers_by_move.get(move_id, [])
                player_args = move_transfers[idx] if idx < len(move_transfers) else None

                entry: dict = {
                    "move": int(move_id) if move_id else 0,
                    "time": int(time),
                    "type": "transfer",
                    "card_name": None,
                    "card_age": None,
                    "card_set": "cities" if args.get("type") == "2" else "base",
                    "from": None,
                    "to": None,
                    "from_owner": None,
                    "to_owner": None,
                    "bottom_to": False,
                }

                if player_args:
                    entry["card_age"] = int(player_args["age"]) if player_args.get("age") is not None else None
                    entry["from"] = player_args.get("location_from")
                    entry["to"] = player_args.get("location_to")
                    entry["from_owner"] = player_names.get(str(player_args.get("owner_from", ""))) or None
                    entry["to_owner"] = player_names.get(str(player_args.get("owner_to", ""))) or None
                    entry["bottom_to"] = bool(player_args.get("bottom_to"))
                    if player_args.get("name"):
                        entry["card_name"] = normalize_hyphens(player_args["name"])
                else:
                    if args.get("age"):
                        entry["card_age"] = int(args["age"])

                if entry["from"] is not None or entry["to"] is not None:
                    log.append(entry)
                continue

            if notif_type in ("log_spectator", "logWithCardTooltips_spectator"):
                log_template = args.get("log") or notif.get("log") or ""
                if not log_template or log_template == "<!--empty-->":
                    continue
                log_msg = clean_html(expand_template(log_template, args))
                if log_msg:
                    log.append({
                        "move": int(move_id) if move_id else 0,
                        "time": int(time),
                        "type": notif_type.replace("_spectator", ""),
                        "msg": log_msg,
                    })

    return {"players": player_names, "log": log}


def main() -> None:
    if len(sys.argv) != 3:
        print("Usage: python -m bga_tracker.innovation.process_log <input_path> <output_path>", file=sys.stderr)
        sys.exit(1)

    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])

    raw_data = json.loads(input_path.read_text(encoding="utf-8"))
    result = process_raw_log(raw_data)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {len(result['log'])} log entries to {output_path}")


if __name__ == "__main__":
    main()

Never prepend `cd` to commands — the working directory is already the project root.
Always use relative paths to project files/folders — never absolute paths (Windows `D:/...` or Unix `/d/...` style).

Always ask clarifying questions before implementing if anything is ambiguous or unclear.

Do not break long single-expression lines (list comprehensions, chained calls, etc.) into multiple lines for PEP 8 compliance. Keep them on one line.

Use type hints on all function parameters and return values. Use modern syntax (`str | None`, `tuple[int, int]`, `list[str]`) — not `typing.Optional`, `typing.Tuple`, etc.

Avoid cryptic abbreviations in variable and attribute names. Use descriptive names (`player_pattern` not `pp`, `card_index` not `ci`).

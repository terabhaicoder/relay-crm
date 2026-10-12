"""Create local-only settings without overwriting an existing environment."""

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    destination = ROOT / ".env"
    if destination.exists():
        print("Existing .env preserved.")
        return
    content = (ROOT / ".env.example").read_text()
    try:
        descriptor = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        print("Existing .env preserved.")
        return
    with os.fdopen(descriptor, "w") as output:
        output.write(content)
    print("Created .env for local SQLite development; no credentials or application user were created.")


if __name__ == "__main__":
    main()

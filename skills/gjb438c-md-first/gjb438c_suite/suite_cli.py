from __future__ import annotations

import sys

from .cli import main


def suite_main() -> int:
    return main(["suite-init", *sys.argv[1:]])


if __name__ == "__main__":
    raise SystemExit(suite_main())

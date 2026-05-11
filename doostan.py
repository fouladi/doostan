#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

from doost import __version__ as doost_version
from doost.util import build_launcher_parser


def main() -> None:
    args = build_launcher_parser().parse_args()

    if args.version:
        print(f"Current version: {doost_version}")
        return

    try:
        from doost.tui import DoostanApp
    except ModuleNotFoundError as error:
        if error.name == "textual":
            raise SystemExit(
                "Textual is required to run Doostan. Install dependencies with "
                "`python -m pip install .` or `python -m pip install textual`."
            ) from error
        raise

    DoostanApp(Path(args.db_path).expanduser()).run()


if __name__ == "__main__":
    main()

from argparse import ArgumentParser, RawTextHelpFormatter
from pathlib import Path

from doost.metadata import read_project_metadata

DEFAULT_BG_COLOR = "#303030"


def build_launcher_parser() -> ArgumentParser:
    """Build the CLI parser for launching the Textual application."""

    project_metadata = read_project_metadata()
    author_names = ", ".join(project_metadata.author_names) or "Unknown"

    parser = ArgumentParser(
        "doostan.py",
        description="Doostan Textual address book manager.",
        epilog=f"Version: {project_metadata.version}\nAuthors: {author_names}",
        formatter_class=RawTextHelpFormatter,
    )
    parser.add_argument(
        "--db-path",
        default=str(Path.home() / ".doost.db"),
        help="Path to the SQLite database file.",
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="Print the current Doostan version and exit.",
    )
    return parser

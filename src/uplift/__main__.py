"""Entry point: python -m uplift upgrade <library>"""

import argparse
import sys

from uplift.orchestrator import upgrade

SUPPORTED_LIBRARIES = {"pydantic"}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="uplift",
        description="Agentic library migration orchestrator",
    )
    sub = parser.add_subparsers(dest="command", metavar="COMMAND")

    upgrade_parser = sub.add_parser(
        "upgrade",
        help="Upgrade a library from v1 to v2",
    )
    upgrade_parser.add_argument(
        "library",
        help=f"Library to upgrade. Supported: {', '.join(sorted(SUPPORTED_LIBRARIES))}",
    )
    upgrade_parser.add_argument(
        "--force",
        action="store_true",
        default=False,
        help=(
            "Ignore cached reports/*.json and regenerate them live. "
            "Runs analyst.extract_breaking_changes(docs/migration-guide.md) and "
            "scanner.scan_usages() from scratch, then continues the normal "
            "migration pipeline.  Useful for demo runs where you want judges to "
            "see the full document→code pipeline execute end-to-end."
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 1

    if args.command == "upgrade":
        if args.library not in SUPPORTED_LIBRARIES:
            print(
                f"Error: unsupported library '{args.library}'. "
                f"Supported: {', '.join(sorted(SUPPORTED_LIBRARIES))}",
                file=sys.stderr,
            )
            return 2
        force: bool = getattr(args, "force", False)
        success = upgrade(args.library, force=force)
        return 0 if success else 1

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())

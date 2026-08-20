"""Apply the end-of-Season promotion and relegation.

Run once, after GW19 is finalized. It reports the twelve managers who change
division and writes nothing unless ``--apply`` is given, because the swap
decides which table each of them is judged in for the whole of Season 2.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from vmf_api.cli.runner import configure_console
from vmf_api.cli.runner import run as run_async
from vmf_api.core.config import get_settings
from vmf_api.core.errors import ConflictError, NotFoundError, RuleValidationError
from vmf_api.db.session import get_engine, get_session_factory
from vmf_api.services.promotion import SwapResult


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Swap the bottom six of HIGH with the top six of LOW after GW19. "
            "Reports what would change unless --apply is given."
        )
    )
    parser.add_argument("--season-code", required=True, help='For example "2026/27".')
    parser.add_argument(
        "--count",
        type=int,
        default=None,
        help="Managers moved in each direction. Defaults to the configured value.",
    )
    parser.add_argument("--apply", action="store_true", help="Write the swap.")
    return parser


async def _run(*, season_code: str, count: int, apply: bool) -> SwapResult:
    from vmf_api.services.promotion import DivisionSwapService

    engine = get_engine()
    try:
        async with get_session_factory()() as session:
            service = DivisionSwapService(session)
            try:
                if not apply:
                    planned, _ = await service.plan(season_code=season_code, count=count)
                    await session.rollback()
                    return planned
                result = await service.apply(season_code=season_code, count=count)
                await session.commit()
                return result
            except Exception:
                await session.rollback()
                raise
    finally:
        await engine.dispose()


def _report(result: SwapResult) -> None:
    mode = "DRY RUN, nothing written" if result.dry_run else "APPLIED"
    print(f"Division swap: {mode}")

    if not result.is_decided:
        print("\n  Blocked. These ranks are shared at a boundary:")
        print("   ", ", ".join(str(rank) for rank in result.contested_ranks))
        print("  The rulebook sends that to an audited administrator decision.")
        return

    print(f"\n  Up to HIGH ({len(result.promoted)}):")
    for move in result.promoted:
        print(f"    LOW {move.finished_rank:>2}  {move.team_name}  ({move.manager_name})")
    print(f"\n  Down to LOW ({len(result.relegated)}):")
    for move in result.relegated:
        print(f"    HIGH {move.finished_rank:>2}  {move.team_name}  ({move.manager_name})")

    if result.dry_run:
        print("\nRe-run with --apply to write it.")
    else:
        print(f"\n  Season 2 memberships written: {result.memberships_written}")


def main(argv: Sequence[str] | None = None) -> int:
    configure_console()
    args = build_parser().parse_args(argv)
    settings = get_settings()
    count = args.count if args.count is not None else settings.promotion_count

    try:
        result = run_async(_run(season_code=args.season_code, count=count, apply=args.apply))
    except (RuleValidationError, ConflictError, NotFoundError, ValueError) as error:
        print(f"Swap aborted: {error}", file=sys.stderr)
        return 2

    _report(result)
    return 0 if result.is_decided else 3


if __name__ == "__main__":
    raise SystemExit(main())

"""Command line: python -m bot.cli <command>.

fetch           fetch all sources, check quality, save snapshots (daily job)
record          forward-record open interest and funding only
check-sources   reachability of every endpoint
backtest        current bot vs DCA (add --final for the logged holdout run)
"""
from __future__ import annotations

import argparse
import sys


def main(argv: list[str] | None = None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass
    ap = argparse.ArgumentParser(prog="bot")
    ap.add_argument("command")
    ap.add_argument("--final", action="store_true", help="evaluate the locked holdout (logged)")
    ap.add_argument("--sources", nargs="*")
    args = ap.parse_args(argv)
    if args.command == "fetch":
        from bot.config import cfg
        from bot.data import update
        st = update.run(args.sources)
        req = [k for k, v in cfg()["sources"].items() if v.get("required")]
        return 0 if all(st["sources"].get(k, {}).get("ok", True) for k in req) else 1
    if args.command == "record":
        from bot.data import update
        update.run(["binance_oi", "binance_funding"])
        return 0
    if args.command == "backtest":
        from bot.backtest import benchmark
        print(benchmark.table(benchmark.run(final=args.final)))
        return 0
    if args.command == "check-sources":
        from bot.data import check_sources
        check_sources.run()
        return 0
    ap.error(f"unknown command {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

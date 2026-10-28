"""Command line: python -m bot.cli <command>.

fetch           fetch all sources, check quality, save snapshots (daily job)
record          forward-record open interest and funding only
check-sources   reachability of every endpoint
backtest        current bot vs DCA (add --final for the logged holdout run)
features        weekly feature table → data/features.parquet
report          weekly recommendation → data/recommendation.json (fail-safe: DCA)
final --final   phase 7: the single logged run on the locked holdout + acceptance criteria
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
    if args.command == "final":
        if not args.final:
            ap.error("the holdout is locked: run `python -m bot.cli final --final` (logged in experiments/final_runs.log)")
        import pickle
        from bot.config import DATA
        from bot.validation import final
        res = final.run()
        (DATA / "derived").mkdir(parents=True, exist_ok=True)
        with open(DATA / "derived" / "final_result.pkl", "wb") as f:
            pickle.dump(res, f)
        print("passed:", res["passed"], [(c["id"], c["ok"]) for c in res["criteria"]])
        return 0
    if args.command == "features":
        from bot.features import build as fb
        fb.weekly(None, write=True)
        return 0
    if args.command == "report":
        from bot.report import vi_report
        print(vi_report.console(vi_report.build()))
        return 0
    if args.command == "check-sources":
        from bot.data import check_sources
        check_sources.run()
        return 0
    ap.error(f"unknown command {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

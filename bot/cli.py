"""Command line: python -m bot.cli <command>.

fetch           fetch all sources, check quality, save snapshots (daily job)
record          forward-record open interest and funding only
check-sources   reachability of every endpoint
backtest        current bot vs DCA (add --final for the logged holdout run)
data-report     part A data-quality report + data/manifest.json
features        weekly feature table → data/features.parquet
report          weekly recommendation → data/recommendation.json (fail-safe: DCA)
final --final   phase 7: the single logged run on the locked holdout + acceptance criteria
forward freeze|log|score   part H forward log in data/forward/ (freeze only after the Part I holdout run)
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
    ap.add_argument("action", nargs="?", help="forward: freeze | log | score")
    ap.add_argument("--asof", help="forward: Sunday (YYYY-MM-DD), default the last weekly close in the data")
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
    if args.command == "data-report":
        from bot.data import manifest
        from bot.report import data_report
        data_report.build()
        manifest.build()
        print("docs/DATA_REPORT.md, data/results/data_quality.json, data/manifest.json")
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
    if args.command == "forward":
        return forward_cmd(ap, args)
    ap.error(f"unknown command {args.command}")
    return 2


def forward_cmd(ap: argparse.ArgumentParser, args) -> int:
    import json

    import pandas as pd

    from bot.config import CONFIG, DATA, load_yaml
    from bot.data import pit_store as ps
    from bot.features import weekly_close as wc
    from bot.models import forward as fw, part_c
    root = DATA / "forward"
    last = pd.Timestamp(ps.load_history("coinmetrics")["date"].max())
    sunday = pd.Timestamp(args.asof) if args.asof else last - pd.Timedelta(days=(last.weekday() + 1) % 7)
    if args.action == "freeze":
        if not (DATA / "results" / "acceptance.json").exists():
            ap.error("chưa có kết quả Phần I (data/results/acceptance.json): đóng băng thật chỉ làm sau lần chạy holdout duy nhất")
        vid, created = fw.freeze(root, sunday, part_c.table)
        print(("đã đóng băng " if created else "phiên bản đã có: ") + vid)
        return 0
    if args.action == "log":
        vdir = fw.current(root)
        log = fw.read_log(vdir)
        start = pd.Timestamp(log["date"].iloc[-1]) + pd.Timedelta(weeks=1) if len(log) else pd.Timestamp(json.loads((vdir / "model.json").read_text(encoding="utf-8"))["state"]["asof"])
        for d in pd.date_range(start, sunday, freq="W-SUN"):
            row = fw.log_week(root, d, part_c.table)
            print(row and f"{row['date']} {row['zone'] or '—'} hệ số {row['mult_used']} late={row['late']}")
        return 0
    if args.action == "score":
        rb = load_yaml(CONFIG / "bot.yaml")["rebuild"]
        vdir = fw.current(root)
        res = fw.score(vdir, wc.load(None), part_c.spec()["forward"]["score_horizons"], rb["bootstrap_n"], rb["seed"], rb["episode_gap_weeks"])
        (vdir / "score.json").write_text(json.dumps(res, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
        print(vdir.name, {k: res.get(k) for k in ("rows", "late", "matured")})
        return 0
    ap.error("forward: freeze | log | score")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

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
acceptance rehearsal       part I on a pretend holdout inside already-seen data (no log, no acceptance file)
acceptance --final         part I: the single logged run on the holdout from 01/01/2024 (refuses a second run)
forecast                   append today's daily price bands to data/forecast/forecast_log.csv (once per anchor day)
entry                      buying price / day tools: append today's band of the lowest price to data/entry/entry_log.csv, write data/results/entry.json
exit                       selling price / day tools: append today's band of the highest price to data/exit/exit_log.csv, write data/results/exit.json
perp                       long/short on the BTCUSDT perpetual: write data/results/perp.json, append today's calls to data/perp/perp_log.csv
trend                      trend forecast 1–7 days, 1–4 weeks, 1–6 months: write data/results/trend.json, append today's forecasts to data/trend/trend_log.csv
perp-trade                 long/short with entry, stop-loss, take-profit: write data/results/perp_trade.json, append the month's pick to data/perp_trade/select_log.csv
final-report               docs/BAO_CAO.md + docs/PHU_LUC.md + docs/img/calib_*.svg from the result files
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
    if args.command == "forecast":
        from bot.models import price_forecast as pf
        cfg = pf.spec()
        rows = pf.log_today(pf.daily_prices(), cfg, pf.utc_now())
        print(f"Dự báo giá: đã ghi {len(rows)} dòng (ngày gốc {rows[0]['issued']}, phiên bản {rows[0]['version']})." if rows
              else "Dự báo giá: ngày gốc mới nhất đã được ghi, không ghi thêm.")
        return 0
    if args.command == "entry":
        from bot.models import entry_timing as et
        rows = et.log_today(et.candles(), et.spec(), et.utc_now())
        et.run(write=True)
        print(f"Giá chờ mua: đã ghi {len(rows)} dòng (ngày gốc {rows[0]['issued']}, phiên bản {rows[0]['version']})." if rows
              else "Giá chờ mua: ngày gốc mới nhất đã được ghi, không ghi thêm.")
        return 0
    if args.command == "exit":
        from bot.models import exit_timing as xt
        rows = xt.log_today(xt.candles(), xt.spec(), xt.utc_now())
        xt.run(write=True)
        print(f"Giá chờ bán: đã ghi {len(rows)} dòng (ngày gốc {rows[0]['issued']}, phiên bản {rows[0]['version']})." if rows
              else "Giá chờ bán: ngày gốc mới nhất đã được ghi, không ghi thêm.")
        return 0
    if args.command == "perp":
        from bot.models import perp_signal as pp
        cfg = pp.spec()
        res = pp.run(write=True)
        rows = pp.log_today(res, pp.build(cfg), cfg, pp.utc_now())
        calls = sum(r["verdict"] != "khong" for r in rows)
        print(f"Long/Short: đã ghi {len(rows)} kỳ hạn (gốc {rows[0]['issued']} UTC, phiên bản {rows[0]['version']}), {calls} kỳ hạn có kết luận vào lệnh."
              if rows else "Long/Short: ngày gốc mới nhất đã được ghi, không ghi thêm.")
        return 0
    if args.command == "trend":
        from bot.models import trend as tr
        res = tr.run(write=True)
        rows = tr.log_today(res, tr.utc_now())
        edge = [r["k"] for r in res["now"] if r["dir_model"] != "goc"]
        print(f"Dự báo xu hướng: gốc {res['anchor']}, {len(res['now'])} kỳ hạn; mô hình thắng tỷ lệ gốc về hướng ở: {edge or 'không kỳ hạn nào'}. "
              + (f"Đã ghi {len(rows)} dòng (phiên bản {res['version']})." if rows else "Ngày gốc đã được ghi, không ghi thêm."))
        return 0
    if args.command == "perp-trade":
        from bot.models import perp_trade as pt
        res = pt.run(write=True)
        rows = pt.log_month(res, pt.utc_now())
        wf, cur = res["wf"], res["current"]
        rule = cur["rule"]["id"] if cur["rule"] else "đứng ngoài"
        print(f"Long/Short có cắt lỗ: tháng {cur['month']} chọn {rule} (t = {cur['t']:.2f}); đi tới từ {wf['from']}: {wf['n']} lệnh, "
              f"thắng {wf['p']:.1%}, R trung bình {wf['meanR']:+.3f}, {'có lợi thế' if wf['edge'] else 'chưa có lợi thế'}. "
              + ("Đã ghi lựa chọn của tháng." if rows else "Lựa chọn của tháng đã có trong nhật ký."))
        for sd, x in res["sides"].items():
            got = f", thắng {x['p']:.1%}, R trung bình {x['meanR']:+.3f}" if x["n"] else f" (đứng ngoài {x['stand_aside']} tháng)"
            print(f"  Riêng {sd}: {x['n']} lệnh đi tới{got}; tiêu chí c1–c4: "
                  + " ".join(f"{k}={'đạt' if v else 'không'}" for k, v in x["check"].items()))
        return 0
    if args.command == "final-report":
        from bot.report import final_report
        r = final_report.build()
        print("docs/BAO_CAO.md, docs/PHU_LUC.md,", len(r["charts"]), "biểu đồ hiệu chỉnh; đạt tiêu chí:", r["passed"])
        return 0
    if args.command == "acceptance":
        from bot.models import part_i
        if args.action == "rehearsal":
            o = part_i.rehearse()
        elif args.final:
            o = part_i.run_final()
        else:
            ap.error("holdout khóa: `acceptance rehearsal` để diễn tập, `acceptance --final` cho lần chạy duy nhất")
        print("passed:", o["passed"], {k: bool(v["pass"]) for k, v in o["criteria"].items()})
        return 0
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
    if not (root / "current.txt").exists():
        print("Chưa có phiên bản đóng băng nào (data/forward/current.txt).")
        return 1
    if args.action == "log":
        vdir = fw.current(root)
        log = fw.read_log(vdir)
        start = pd.Timestamp(log["date"].iloc[-1]) + pd.Timedelta(weeks=1) if len(log) else pd.Timestamp(json.loads((vdir / "model.json").read_text(encoding="utf-8"))["state"]["asof"])
        weeks = pd.date_range(start, sunday, freq="W-SUN")
        try:
            for d in weeks:
                row = fw.log_week(root, d, part_c.table)
                print(row and f"{vdir.name}: đã ghi tuần {row['date']}, khung {row['zone'] or '—'}, hệ số dùng {row['mult_used']}, ghi muộn {row['late']}")
        except fw.ModelChanged as e:
            print(f"Không ghi: mã hoặc cấu hình đã đổi so với phiên bản {vdir.name} ({e}). Nhật ký cũ giữ nguyên; muốn tiếp tục thì đóng băng phiên bản mới.")
            return 1
        if not len(weeks):
            print(f"{vdir.name}: chưa có giá đóng tuần mới để ghi (tuần cuối đã ghi {log['date'].iloc[-1] if len(log) else '—'}).")
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

"""RSI joined with price action, as a direction forecast for the Trend view (config/candidates.yaml, section pa_rsi;
registered before any number was computed).

Each of the 12 registered price action signals (price_action.flags: 10 criteria + 2 confluence sets) is joined with an
RSI 14 condition in 3 fixed ways (strict 30/70 reversal, lean-reversal around 50, lean-trend around 50). Every pair is
scored exactly like section price_action (price_action.table: same days, horizons, baseline, bootstrap, halves, Holm over
the 144 pairs). A join only "adds benefit" when it beats any day (verdict 'hon') AND beats the price action signal alone
AND beats the RSI condition alone, in both halves. Only then may it go on the page.
"""
from __future__ import annotations

import hashlib
import json

import numpy as np
import pandas as pd

from bot.config import CONFIG, DATA, ROOT, load_yaml
from bot.models import price_action as pa
from bot.models import rsi_check as rc

VARIANTS = ("qua_ban_mua", "nghieng_dao_chieu", "nghieng_xu_huong")


def spec() -> dict:
    return load_yaml(CONFIG / "candidates.yaml")["pa_rsi"]


def version(cfg: dict) -> str:
    code = b"".join((ROOT / "bot" / "models" / f).read_bytes().replace(b"\r\n", b"\n") for f in ("pa_rsi.py", "price_action.py", "rsi_check.py"))
    return hashlib.sha256(json.dumps(cfg, sort_keys=True, ensure_ascii=False, default=str).encode() + code).hexdigest()[:10]


def rsi_ok(R: np.ndarray, variant: str, s: int) -> np.ndarray:
    """The RSI condition of a join for a signal of direction s (+1 rise, −1 fall); NaN RSI → False."""
    with np.errstate(invalid="ignore"):
        if variant == "qua_ban_mua":
            return (R < 30) if s > 0 else (R > 70)
        if variant == "nghieng_dao_chieu":
            return (R < 50) if s > 0 else (R > 50)
        if variant == "nghieng_xu_huong":
            return (R > 50) if s > 0 else (R < 50)
    raise ValueError(variant)


def _cfg(names: dict[str, int], horizons) -> dict:
    """A price_action-shaped config so price_action.table scores these columns (direction = first word)."""
    return {"criteria": {k: ("tăng" if s > 0 else "giảm") for k, s in names.items()}, "combo": {}, "horizons_days": list(horizons)}


def build(d: pd.DataFrame, pcfg: dict) -> tuple[pd.DataFrame, dict, pd.DataFrame, dict, pd.DataFrame, dict]:
    """Joined signals, the price action signals alone and the RSI conditions alone, each with its directions."""
    f = pa.flags(d, pcfg)
    dirs = pa.direction(pcfg)
    R = rc.rsi_series(d["close"]).to_numpy()
    joined, jd, alone_r, rd = {}, {}, {}, {}
    for v in VARIANTS:
        for s in (1, -1):
            alone_r[f"rsi|{v}|{s}"] = rsi_ok(R, v, s)
            rd[f"rsi|{v}|{s}"] = s
        for name, s in dirs.items():
            joined[f"{name}|{v}"] = f[name].to_numpy() & rsi_ok(R, v, s)
            jd[f"{name}|{v}"] = s
    return (pd.DataFrame(joined, index=d.index), jd, f, dirs, pd.DataFrame(alone_r, index=d.index), rd)


def evaluate(d: pd.DataFrame, pcfg: dict, n_boot: int = pa.N_BOOT) -> dict:
    J, jd, F, fd, A, ad = build(d, pcfg)
    hz = [int(x) for x in pcfg["horizons_days"]]
    r = pcfg["research"]
    start, end = pd.Timestamp(str(r["from"])), pd.Timestamp(str(r["to"]))
    rows = pa.table(d, J, _cfg(jd, hz), start, end, n_boot=n_boot)                       # Holm over the 144 joined pairs
    # mốc so sánh: price action một mình, RSI một mình (chỉ cần tỷ lệ đúng từng nửa; bootstrap ít lần cho nhanh)
    pa_rows = {(x["crit"], x["k"]): x for x in pa.table(d, F, _cfg(fd, hz), start, end, n_boot=50)}
    rsi_rows = {(x["crit"], x["k"]): x for x in pa.table(d, A, _cfg(ad, hz), start, end, n_boot=50)}
    for x in rows:
        sig, v = x["crit"].rsplit("|", 1)
        x["signal"], x["variant"] = sig, v
        p_alone, r_alone = pa_rows[(sig, x["k"])], rsi_rows[(f"rsi|{v}|{x['dir']}", x["k"])]
        x["pa_alone"] = {"hit": p_alone["hit"], "n": p_alone["n"], "halves": [h["hit"] for h in p_alone["halves"]]}
        x["rsi_alone"] = {"hit": r_alone["hit"], "n": r_alone["n"], "halves": [h["hit"] for h in r_alone["halves"]]}
        beats = lambda other: all(a is not None and b is not None and a > b  # noqa: E731
                                  for a, b in zip([h["hit"] for h in x["halves"]], other["halves"]))
        x["beats_pa"], x["beats_rsi"] = beats(x["pa_alone"]), beats(x["rsi_alone"])
        x["benefit"] = bool(x["verdict"] == "hon" and x["beats_pa"] and x["beats_rsi"])
    counts = {v: sum(x["verdict"] == v for x in rows) for v in ("hon", "kem", "chua", "it_dot")}
    return {"rows": rows, "counts": counts, "n_pairs": len(rows), "benefit": [x["crit"] + f"|{x['k']}" for x in rows if x["benefit"]],
            "from": str(r["from"]), "to": str(r["to"])}


def markdown(o: dict) -> str:
    VN = {"hon": "hơn mốc", "kem": "kém mốc", "chua": "chưa có lợi thế", "it_dot": "ít đợt"}
    VV = {"qua_ban_mua": "quá bán/mua 30–70", "nghieng_dao_chieu": "nghiêng đảo chiều (50)", "nghieng_xu_huong": "nghiêng xu hướng (50)"}
    c = o["counts"]
    L = ["# RSI ghép với price action (mục `pa_rsi`)", "",
         f"Đăng ký trước trong `config/candidates.yaml` mục `pa_rsi`; chạy `python -m bot.cli pa-rsi`. Phiên bản {o['version']}.",
         f"Giai đoạn nghiên cứu {o['from']} → {o['to']}, nến ngày Bitstamp, cách chấm giống hệt mục `price_action`.", "",
         "## Kết luận", "",
         f"- {o['n_pairs']} cặp (12 tín hiệu price action × 3 cách ghép RSI × 4 kỳ hạn), Holm trên {o['n_pairs']} cặp.",
         f"- Hơn một ngày bất kỳ: **{c['hon']}**; kém: {c['kem']}; chưa có lợi thế: {c['chua']}; ít đợt (không kết luận): {c['it_dot']}.",
         f"- Làm tăng lợi ích (hơn ngày bất kỳ, hơn price action một mình và hơn RSI một mình ở cả hai nửa): **{len(o['benefit'])}**.",
         ("- Theo quy tắc đã đăng ký và lời người dùng: **không dùng** cách ghép nào, thẻ Xu hướng giữ nguyên."
          if not o["benefit"] else "- Có cách ghép đạt: " + ", ".join(o["benefit"]) + " (cần xác nhận trên dữ liệu mới từ 12/11/2026)."),
         "", "## Từng cặp", "",
         "| Tín hiệu | Cách ghép RSI | Kỳ hạn | Số ngày | Đợt | Đúng | Ngày bất kỳ | PA một mình | RSI một mình | p Holm | Nhãn |",
         "|---|---|---|---|---|---|---|---|---|---|---|"]
    f = lambda x: "—" if x is None else f"{x:.0%}"  # noqa: E731
    for x in sorted(o["rows"], key=lambda r: (r["signal"], r["variant"], r["k"])):
        L.append(f"| {x['signal']} | {VV[x['variant']]} | {x['k']} | {x['n']} | {x['episodes']} | {f(x['hit'])} | {f(x['base'])} | "
                 f"{f(x['pa_alone']['hit'])} | {f(x['rsi_alone']['hit'])} | {x['p_holm']:.2f} | {VN[x['verdict']]}{' · **dùng được**' if x['benefit'] else ''} |")
    L += ["", "Công cụ tham khảo, không phải lời khuyên đầu tư.", ""]
    return "\n".join(L)


def run(write: bool = True, n_boot: int = pa.N_BOOT) -> dict:
    cfg, pcfg = spec(), pa.spec()
    d = pa.daily()
    o = evaluate(d, pcfg, n_boot=n_boot)
    o["version"] = version(cfg)
    if write:
        (DATA / "results").mkdir(exist_ok=True)
        slim = {**o, "rows": [{k: v for k, v in x.items() if k not in ("halves",)} | {"halves": [{kk: h[kk] for kk in ("n", "episodes", "hit", "base", "diff")} for h in x["halves"]]}
                              for x in o["rows"]]}
        (DATA / "results" / "pa_rsi.json").write_text(json.dumps(slim, ensure_ascii=False, separators=(",", ":"), default=str), encoding="utf-8")
        (ROOT / "docs" / "PA_RSI.md").write_text(markdown(o), encoding="utf-8", newline="\n")
    return o

#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""全スポットの「犬が入れるか」を2つのエージェントで別々に調べ、突き合わせる（2026-09-28導入）。

なぜ要るか:
  小目津公園（公式が園内の犬の散歩を禁止）が掲載されたままになっていた。更新タスクが順番に回れば1か月かかるので、
  犬の可否だけに絞って全件を一度に見直す。Codexは使わず、Claudeのエージェント2体に**違う役目**を持たせて比べる
  （同じClaude2体は同じ勘違いをしやすい。役目を変えると片方だけの勘違いが浮く）。

役目:
  A（公式を読む役）… officialUrl を開き、ペット・犬の記載を探して分類する
  B（載せない根拠を探す役）… Aの答えは見せない。「この施設に犬を連れて行けない理由」を公式・自治体・施設SNSから探す
判定の語（両方共通）:
  ban        … 範囲を限らず犬・ペットの立ち入り／散歩／同伴を禁止（＝掲載しない施設）
  partial    … 一部のエリア・建物・時間帯だけ不可（＝掲載可。remarks に範囲を書く）
  allowed    … 可と明記
  no_mention … 犬・ペットの記載を見つけられない
  unreachable… 公式を開けない

使い方:
  python scripts/dog_ban_audit.py bundles --size 10 --out DIR   … 束ごとのプロンプト用JSON（spots_XX.json）を書く
  python scripts/dog_ban_audit.py merge --dir DIR --out RESULT.json … A_XX.json と B_XX.json を突き合わせて結果を書く
  python scripts/dog_ban_audit.py report --result RESULT.json     … 人が読む一覧（決着が要るもの・確定したもの）
エージェントの答えは1件ずつ {"id","verdict","quote","url","note"} の配列で、A_XX.json / B_XX.json に保存する。
"""
import argparse
import json
import sys
from collections import Counter
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
SPOTS = PROJECT / "data" / "spots.json"
VERDICTS = {"ban", "partial", "allowed", "no_mention", "unreachable"}


def load_spots():
    return json.loads(SPOTS.read_text(encoding="utf-8"))


def cmd_bundles(a):
    spots = load_spots()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    n = 0
    for i in range(0, len(spots), a.size):
        chunk = spots[i:i + a.size]
        items = [{"id": s["id"], "name": s["name"], "address": s.get("address", ""),
                  "officialUrl": s.get("officialUrl", ""),
                  # Bだけに渡す補助（remarks は結論を含むので A にも B にも渡さない）
                  "aliases": s.get("aliases", [])} for s in chunk]
        (out / f"spots_{n:02d}.json").write_text(json.dumps(items, ensure_ascii=False, indent=1), encoding="utf-8")
        n += 1
    print(f"束 {n}個（{a.size}件ずつ・計{len(spots)}件）→ {out}")


def _load_answers(d: Path, prefix: str) -> dict:
    ans = {}
    for f in sorted(d.glob(f"{prefix}_*.json")):
        try:
            arr = json.loads(f.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"!! 読めない {f.name}: {e}")
            continue
        for x in arr:
            if not isinstance(x, dict) or "id" not in x:
                continue
            v = str(x.get("verdict", "")).strip()
            if v not in VERDICTS:
                x["verdict"] = "unreachable"; x["note"] = f"(想定外の判定 {v!r}) " + str(x.get("note", ""))
            ans[x["id"]] = x
    return ans


def cmd_merge(a):
    d = Path(a.dir)
    A, B = _load_answers(d, "A"), _load_answers(d, "B")
    spots = load_spots()
    rows = []
    for s in spots:
        sid = s["id"]
        ra, rb = A.get(sid), B.get(sid)
        va = ra["verdict"] if ra else "missing"
        vb = rb["verdict"] if rb else "missing"
        if va == "ban" and vb == "ban":
            status = "ban_agreed"          # 両方が犬禁止 → 人に渡す（外す候補）
        elif "ban" in (va, vb):
            status = "ban_disputed"        # 片方だけ犬禁止 → Claudeが公式を開いて決着
        elif "missing" in (va, vb):
            status = "incomplete"          # どちらかの答えが無い
        elif va == "partial" or vb == "partial":
            status = "partial"             # 一部不可 → 掲載可。remarks に範囲があるか後で見る
        else:
            status = "ok"
        rows.append({"id": sid, "name": s["name"], "status": status, "A": ra, "B": rb})
    Path(a.out).write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    c = Counter(r["status"] for r in rows)
    print("突き合わせ:", dict(c), "→", a.out)


def cmd_report(a):
    rows = json.loads(Path(a.result).read_text(encoding="utf-8"))
    order = ["ban_agreed", "ban_disputed", "incomplete", "partial", "ok"]
    label = {"ban_agreed": "★両方が犬禁止（外す候補・人が決める）", "ban_disputed": "★片方だけ犬禁止（Claudeが公式で決着）",
             "incomplete": "答えが揃っていない", "partial": "一部のみ不可（掲載可）", "ok": "問題なし"}
    for st in order:
        rs = [r for r in rows if r["status"] == st]
        if not rs:
            continue
        print(f"\n== {label[st]}: {len(rs)}件")
        if st in ("ban_agreed", "ban_disputed", "incomplete"):
            for r in rs:
                print(f"- {r['id']} {r['name']}")
                for k in ("A", "B"):
                    x = r[k]
                    if x:
                        print(f"    {k}: {x['verdict']} | {str(x.get('quote', ''))[:90]} | {x.get('url', '')}")
                    else:
                        print(f"    {k}: （答えなし）")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("bundles"); p.add_argument("--size", type=int, default=10); p.add_argument("--out", required=True)
    p = sub.add_parser("merge"); p.add_argument("--dir", required=True); p.add_argument("--out", required=True)
    p = sub.add_parser("report"); p.add_argument("--result", required=True)
    a = ap.parse_args()
    {"bundles": cmd_bundles, "merge": cmd_merge, "report": cmd_report}[a.cmd](a)


if __name__ == "__main__":
    main()

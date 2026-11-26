"""シーズン前の見直し（get_next_check_targets.py の季節の割り込みと update_check_count.py の結果の記録）の試験。
期間・選び方・記録の形を変えたら流す: python scripts/test_season_priority.py
需要と進捗は試験用の固定のファイルを使う（本物の進捗ファイルには書かない）。
"""
import io
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

R = Path(__file__).resolve().parent.parent
T = Path(tempfile.mkdtemp(prefix="season_test_"))
sys.path.insert(0, str(R / "scripts"))
import datetime  # noqa: E402
from season_windows import season_status, active_seasons  # noqa: E402

spots = json.load(io.open(R / "data" / "spots.json", encoding="utf-8-sig"))
koyo = [s["id"] for s in spots if "koyo" in (s.get("tags") or [])]
sakura = [s["id"] for s in spots if "sakura" in (s.get("tags") or [])]
other = [s["id"] for s in spots if s["id"] not in koyo]

# 需要は固定: 紅葉の名所の最後の1件を1位、最後から2件目を2位にする（回数の少ない順・並び順と食い違うように）
K1, K2 = koyo[-1], koyo[-2]
# 期限の再確認の試験用: 紅葉でないスポット6件に、2027-10-15 まで の temporary を入れた spots
EXP = other[:6]
fx = json.loads(json.dumps(spots))
for sp in fx:
    sp.pop("temporary", None)
    if sp["id"] in EXP:
        sp["temporary"] = [{"note": "試験用の期限付きの情報", "until": "2027-10-15", "source": "https://example.com/", "onExpire": "試験"}]
FIX_SPOTS = T / "spots_fixture.json"
FIX_SPOTS.write_text(json.dumps(fx, ensure_ascii=False), encoding="utf-8")
DEMAND = T / "demand.json"
DEMAND.write_text(json.dumps({"spots": {K1: {"clicks": 500}, K2: {"clicks": 300}}}), encoding="utf-8")


def run(today, progress, extra=(), demand=DEMAND, expiry=False, spots_file=FIX_SPOTS):
    pp = T / "prog.json"
    pp.write_text(json.dumps(progress), encoding="utf-8")
    args = [sys.executable, str(R / "scripts" / "get_next_check_targets.py"), "--count", "5",
            "--today", today, "--progress", str(pp), "--demand", str(demand), "--spots", str(spots_file), *extra]
    if not expiry:
        args.append("--no-expiry-priority")
    r = subprocess.run(args, capture_output=True, text=True, encoding="utf-8",
                       env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    if r.returncode != 0:
        return None, r.stderr
    return json.loads(r.stdout), r.stderr


ok = True


def check(name, cond):
    global ok
    print(("OK  " if cond else "NG  ") + name)
    ok &= bool(cond)


def season_ids(out):
    return [r["id"] for r in (out or []) if r.get("reason") == "シーズン前の見直し"]


base = lambda: {"check_counts": {s["id"]: 5 for s in spots},
                "last_checked": {s["id"]: "2027-09-01" for s in spots}}

# 1) 需要1位が割り込む（回数が多くても）
p = base(); p["check_counts"][K1] = 50
out, err = run("2027-10-10", p)
check("需要1位が1件だけ割り込む", season_ids(out) == [K1])
check("ログに入ったと出る", ("今日の対象に入った: " + K1) in err)

# 2) 期間中に見て結果を書き忘れた → 発表待ち扱いで14日は割り込まない、14日後にまた入る
p["last_checked"][K1] = "2027-10-10"
out, _ = run("2027-10-11", p)
check("見た翌日は次の需要順位へ", season_ids(out) == [K2])
p["last_checked"][K2] = "2027-10-11"
p["last_checked"].update({k: "2027-10-12" for k in koyo if k not in (K1, K2)})
out, err = run("2027-10-23", p)
check("発表待ちは14日たつまで入らない", season_ids(out) == [])
out, _ = run("2027-10-24", p)
check("14日たったら需要順でまた入る", season_ids(out) == [K1])

# 3) 済みにしたものは二度と入らない
p["season_checks"] = {"2027-koyo": {K1: {"date": "2027-10-10", "result": "done"}}}
out, err = run("2027-10-25", p)
check("済みは入らない（次の発表待ちが入る）", season_ids(out) == [K2] and "済み 1件" in err)

# 4) 期間の前日・翌日は割り込まない
for d in ("2027-09-30", "2027-11-21"):
    o, e = run(d, base())
    check(d + " は割り込まない", season_ids(o) == [] and "[season]" not in e)

# 5) 期間中の紅葉スポットには理由にかかわらず season_check が付く
o, _ = run("2027-10-10", base())
check("紅葉スポットだけに season_check", all(("season_check" in r) == (r["id"] in koyo) for r in o))

# 6) 0で止まる
o, _ = run("2027-10-10", base(), ("--seasonal-slots", "0"))
check("--seasonal-slots 0 で止まる", season_ids(o) == [])

# 7) 2枠の時も需要順が保たれる（回数の少ない2位が1位を押し出さない）
p = base(); p["check_counts"][K2] = 0
o, _ = run("2027-10-10", p, ("--seasonal-slots", "2"))
check("2枠は需要1位・2位の順", season_ids(o) == [K1, K2])

# 8) 桜の期間
o, _ = run("2027-03-15", {"check_counts": {}, "last_checked": {}})
check("桜の期間は桜から1件", len(season_ids(o)) == 1 and season_ids(o)[0] in sakura
      and [r for r in o if r["id"] == season_ids(o)[0]][0]["season_check"][0]["season"] == "sakura")

# 9) 今日見たスポットは後ろへ回る（深夜に見たものを昼にまた選ばない）
p = {"check_counts": {s["id"]: 5 for s in spots}, "last_checked": {}}
low = other[:3]
for x in low:
    p["check_counts"][x] = 0
    p["last_checked"][x] = "2027-06-01"
o, _ = run("2027-06-01", p)
check("今日見たものは後ろへ", not any(r["id"] in low for r in o))

# 10) 壊れた入力で止まらない
for name, prog in (("last_checked が null", {"check_counts": {}, "last_checked": None}),
                   ("日付が数値・配列", {"check_counts": {}, "last_checked": {k: 20271001 for k in koyo[:3]} | {k: [1] for k in koyo[3:6]}}),
                   ("check_counts に文字列", {"check_counts": {k: "x" for k in koyo}, "last_checked": {}}),
                   ("season_checks が壊れている", {"season_checks": {"2027-koyo": "x"}, "last_checked": {}})):
    o, e = run("2027-10-10", prog)
    check("壊れた入力でも止まらない: " + name, o is not None and len(o) == 5)
bad = T / "bad_demand.json"
bad.write_text(json.dumps({"spots": {K1: {"clicks": "999"}}}), encoding="utf-8")
o, e = run("2027-10-10", base(), demand=bad)
check("需要のクリック数が文字列でも止まらない", o is not None and "読めない行 1件" in e)
o, e = run("2027-10-10", base(), demand=T / "nope.json")
check("需要ファイルが無くても止まらない", o is not None and "需要ファイルを読めない" in e)

# 11) 未来の日付は「見た」に数えない
s0 = active_seasons(datetime.date(2027, 10, 10))[0]
check("未来の日付は見ていない扱い",
      season_status(K1, s0, datetime.date(2027, 10, 10), {}, {K1: "2027-11-01"})[0] == "unseen")

# 12) 期限の再確認で枠が埋まると季節は入らず、ログに出る（試験用の temporary 6件が期限の5日前）
o, e = run("2027-10-10", base(), expiry=True)
reasons = [r.get("reason") for r in o]
check("期限の再確認が5枠を埋める", reasons.count("期限の再確認") == 5)
check("期限で枠が埋まった日は季節が入らないと出る", ("枠が埋まって入らなかった: " + K1) in e)

# 13) update_check_count.py が季節の結果を書く（後から発表待ちを渡されたら発表待ちにする・期間外は書かない）
up = T / "prog_uc.json"
up.write_text("{}", encoding="utf-8")
uc = [sys.executable, str(R / "scripts" / "update_check_count.py"), "--progress", str(up)]
env = dict(os.environ, PYTHONIOENCODING="utf-8")
subprocess.run(uc + ["--ids", K1 + "," + other[0], "--season-done", K1, "--season-wait", other[0], "--today", "2027-10-10"],
               capture_output=True, env=env)
subprocess.run(uc + ["--ids", K1, "--season-wait", K1, "--today", "2027-10-12"], capture_output=True, env=env)
sc = json.loads(up.read_text(encoding="utf-8")).get("season_checks", {})
check("季節の結果を書く（後の発表待ちが勝つ・期間外は書かない）",
      sc.get("2027-koyo", {}).get(K1) == {"date": "2027-10-12", "result": "wait"} and other[0] not in sc.get("2027-koyo", {}))

# 13b) 期間外の日（紅葉の翌日）は紅葉の名所でも書かない
up.write_text("{}", encoding="utf-8")
subprocess.run(uc + ["--ids", K1, "--season-done", K1, "--today", "2027-11-21"], capture_output=True, env=env)
check("期間外の日は紅葉の名所でも書かない", not json.loads(up.read_text(encoding="utf-8")).get("season_checks"))

# 14) 期限の再確認: 今日見たものは入れない・未来の日付は止める理由にしない
e1 = EXP[0]
for d in ("2027-10-10", "2027-10-14"):  # ふだんの日と、終わる日の前後3日（毎日見る日）
    p = base(); p["last_checked"][e1] = d
    o, e = run(d, p, expiry=True)
    check("今日見たものは期限の再確認でも入らない: " + d, e1 not in [r["id"] for r in o])
p = base(); p["last_checked"][e1] = "2028-01-01"
o, e = run("2027-10-10", p, expiry=True)
check("未来の日付は期限の再確認を止めない", e1 in [r["id"] for r in o if r.get("reason") == "期限の再確認"])

# 15) 期間外の日付の「済み」は済みに数えない
s0 = active_seasons(datetime.date(2027, 10, 10))[0]
for d in ("2027-09-30", "2027-10-11"):
    check("期間外・未来の済みは数えない: " + d,
          season_status(K1, s0, datetime.date(2027, 10, 10), {"2027-koyo": {K1: {"date": d, "result": "done"}}}, {})[0] != "done")

# 16) 記録: --ids に無いIDは書かない・両方に入れたら発表待ち・壊れた形でも止まらない
up.write_text(json.dumps({"last_checked": None, "check_counts": [], "season_checks": {"2027-koyo": "x"}}), encoding="utf-8")
r = subprocess.run(uc + ["--ids", K1, "--season-done", K1 + "," + K2, "--season-wait", K1, "--today", "2027-10-10"],
                   capture_output=True, text=True, encoding="utf-8", env=env)
sc = json.loads(up.read_text(encoding="utf-8")).get("season_checks", {}).get("2027-koyo", {})
check("記録: 壊れた形でも止まらない", r.returncode == 0)
check("記録: 両方に入れたら発表待ち", sc.get(K1, {}).get("result") == "wait")
check("記録: --ids に無いIDは書かない", K2 not in sc)

# 17) 期間の最終日に、済みにならなかった名所を出す
o, e = run("2027-11-20", base())
check("最終日に残りを出す", "期間の最終日。この回の対象を除いて済みになっていない名所" in e)
picked = season_ids(o)
check("最終日の残りにこの回の対象を入れない", bool(picked) and ("," + picked[0] + ",") not in ("," + e.split("済みになっていない名所")[1].split(":", 1)[1].strip().split("\n")[0] + ","))

# 18) 14日たった需要の多い発表待ちは、需要の少ない未確認より先に入る
p = base(); p["last_checked"][K1] = "2027-10-01"
o, _ = run("2027-10-15", p)
check("14日たった需要1位の発表待ちが未確認より先", season_ids(o) == [K1])

print("ALL OK" if ok else "FAILED")
sys.exit(0 if ok else 1)

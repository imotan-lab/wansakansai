"""スポットに「掲載情報の最終確認日」（lastChecked）を書く。詳細ページに「掲載情報の最終確認：YYYY年M月D日」と出る。

なぜ要るか（2026-10-10）:
  AdSenseの対策（編集されたメディアとして見せる）。読む人にとっても、情報がいつ時点のものかが分かる。
  スポット更新タスク（am/pm）が毎日5件ずつ公式を見直しているので、その日付をそのまま出す。

使い方:
  python scripts/stamp_last_checked.py --ids id1,id2,...        … 今日の日付を書く（スポット更新タスクが STEP 8 で使う）
  python scripts/stamp_last_checked.py --ids ... --date 2026-10-07
  python scripts/stamp_last_checked.py --backfill               … 過去のログと進捗ファイルから、各スポットの最後に確かめた日を埋める（初回だけ）

書くのは spots.json の "lastChecked": "YYYY-MM-DD" だけ。日付は新しくなる向きにしか変えない。
ログ: C:/Users/imao_/.claude/logs/spot_check_YYYY-MM-DD.log に追記しない（呼んだタスクが自分のログに書く）。結果は標準出力。
"""
import argparse, datetime, json, re, sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parent.parent
SPOTS = ROOT / "data" / "spots.json"
LOGS = Path(r"C:\Users\imao_\.claude\logs")
PROGRESS = Path(r"C:\Users\imao_\Documents\wansakansai\spot_check_progress.json")
DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")


def set_dates(dates: dict) -> list:
    """dates={id: 'YYYY-MM-DD'} を spots.json に書く。書式を崩さないよう該当スポットの行だけ書き換える。"""
    s = SPOTS.read_text(encoding="utf-8")
    changed = []
    for sid, d in dates.items():
        m = re.search(r'\n    "id": "' + re.escape(sid) + r'",\n', s)
        if not m:
            continue
        end = s.find('\n  }', m.end())
        block = s[m.start():end]
        cur = re.search(r'\n    "lastChecked": "(\d{4}-\d{2}-\d{2})",?', block)
        if cur:
            if cur.group(1) >= d:
                continue
            nb = block.replace(cur.group(0), cur.group(0).replace(cur.group(1), d))
        else:
            # id の行の直後に足す（どのスポットでも同じ位置になり、差分が読みやすい）
            nb = block.replace(m.group(0), m.group(0) + f'    "lastChecked": "{d}",\n', 1)
        s = s[:m.start()] + nb + s[end:]
        changed.append((sid, cur.group(1) if cur else None, d))
    json.loads(s)  # 壊れていないか
    SPOTS.write_text(s, encoding="utf-8", newline="")
    return changed


def backfill() -> dict:
    """スポット更新タスクのログ「チェック対象: [id(count=n), ...]」と進捗ファイルの last_checked から、最後に確かめた日を集める。"""
    found = {}
    for f in sorted(LOGS.glob("spot_check_*.log")):
        m = re.search(r"spot_check_(\d{4}-\d{2}-\d{2})\.log$", f.name)
        if not m:
            continue
        day = m.group(1)
        for line in f.read_text(encoding="utf-8", errors="replace").splitlines():
            if "チェック対象" not in line:
                continue
            for sid in re.findall(r"([a-z0-9][a-z0-9-]+)\(count=", line):
                found[sid] = max(found.get(sid, ""), day)
    try:
        prog = json.loads(PROGRESS.read_text(encoding="utf-8")).get("last_checked", {})
        for sid, d in prog.items():
            d = str(d)[:10]
            if DATE_RE.fullmatch(d):
                found[sid] = max(found.get(sid, ""), d)
    except FileNotFoundError:
        pass
    return found


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--ids")
    g.add_argument("--backfill", action="store_true")
    ap.add_argument("--date", default=f"{datetime.date.today():%Y-%m-%d}")
    a = ap.parse_args()
    ids = {s["id"] for s in json.loads(SPOTS.read_text(encoding="utf-8"))}
    if a.backfill:
        dates = {k: v for k, v in backfill().items() if k in ids}
    else:
        if not DATE_RE.fullmatch(a.date):
            print("--date は YYYY-MM-DD")
            return 2
        want = [x.strip() for x in a.ids.split(",") if x.strip()]
        bad = [w for w in want if w not in ids]
        if bad:
            print("spots.json に無いID:", ", ".join(bad))
            return 2
        dates = {w: a.date for w in want}
    changed = set_dates(dates)
    for sid, old, new in changed:
        print(f"[lastChecked] {sid}: {old or '（なし）'} → {new}")
    print(f"=== 書いた {len(changed)}件 / 対象 {len(dates)}件 / 全{len(ids)}件中 未設定 {len(ids) - len([1 for s in json.loads(SPOTS.read_text(encoding='utf-8')) if s.get('lastChecked')])}件 ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""未投稿の新スポットを、キューの先頭から1件Xに投稿する。

今日のおすすめ投稿（post_daily_spot.py）の前に daily-spot タスクが呼ぶ。1日1件なので、
キューに残りがある日は今日のおすすめの代わりに新スポットを出す。

  終了コード 2 … キューが空。何もしない（→ タスクは今日のおすすめを投稿する）
  終了コード 0 … 投稿した。先頭をキューから外した（→ 今日の投稿はこれで終わり）
  終了コード 1 … 投稿に失敗。先頭は残す（→ 翌日にもう一度。タスクは今日のおすすめを投稿する）

結果は scripts/new_spot_post_status.json にも書く（date / result / spot_id / remaining）。
バックグラウンド実行で終了コードを取りにくい時はこちらを読む。

キュー: scripts/new_spot_queue.json … ["spot-id", ...] を先頭から順に投稿する。
        merge_new_spots.py --apply が取り込んだIDを末尾に足す。手で並べ替えてよい。

使い方:
  python scripts/post_next_new_spot.py            # 実投稿（post_new_spot.py と同じ5〜20分の遅延あり）
  python scripts/post_next_new_spot.py --dry-run  # 投稿せず本文だけ確認。キューは変えない
  python scripts/post_next_new_spot.py --list     # キューの中身を表示
"""
import datetime, io, json, os, subprocess, sys

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
QUEUE = os.path.join(HERE, "new_spot_queue.json")
STATUS = os.path.join(HERE, "new_spot_post_status.json")
SPOTS = os.path.join(ROOT, "data", "spots.json")
HISTORY = os.path.join(HERE, "x_post_history.json")
POSTER = os.path.join(HERE, "post_new_spot.py")


def load_queue():
    if not os.path.exists(QUEUE):
        return []
    q = json.load(io.open(QUEUE, encoding="utf-8"))
    return [x for x in q if isinstance(x, str) and x]


def save_queue(q):
    io.open(QUEUE, "w", encoding="utf-8").write(json.dumps(q, ensure_ascii=False, indent=2) + "\n")


def write_status(result, spot_id, remaining, note=""):
    io.open(STATUS, "w", encoding="utf-8").write(json.dumps({
        "date": datetime.date.today().isoformat(),
        "result": result,          # posted / empty / failed / dry-run
        "spot_id": spot_id,
        "remaining": remaining,
        "note": note,
    }, ensure_ascii=False, indent=2) + "\n")


def already_posted(spot_id):
    if not os.path.exists(HISTORY):
        return False
    h = json.load(io.open(HISTORY, encoding="utf-8"))
    posts = h.get("posts", []) if isinstance(h, dict) else h
    return any(p.get("spot_id") == spot_id and p.get("post_type") == "new_spot" for p in posts)


def main():
    args = sys.argv[1:]
    q = load_queue()
    spots = {s["id"]: s for s in json.load(io.open(SPOTS, encoding="utf-8"))}

    if "--list" in args:
        print(f"キュー {len(q)} 件")
        for i, sid in enumerate(q, 1):
            name = spots.get(sid, {}).get("name", "（spots.json に無い）")
            mark = "投稿済み" if already_posted(sid) else ""
            print(f"  {i}. {sid}  {name}  {mark}")
        return 0

    # 先頭から、存在しないID・投稿済みIDは外す（投稿しないのに残っていると毎日同じ所で止まる）
    while q:
        sid = q[0]
        if sid not in spots:
            print(f"[queue] {sid} は spots.json に無いので外す")
            q.pop(0); save_queue(q); continue
        if already_posted(sid):
            print(f"[queue] {sid} は new_spot として投稿済みなので外す")
            q.pop(0); save_queue(q); continue
        break

    if not q:
        print("[queue] 未投稿の新スポットなし。今日のおすすめを投稿する")
        write_status("empty", "", 0)
        return 2

    sid = q[0]
    print(f"[queue] 先頭 {sid}（{spots[sid]['name']}）を投稿する。残り {len(q)} 件")
    passthrough = [a for a in args if a in ("--dry-run", "--no-jitter")]
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    r = subprocess.run([sys.executable, POSTER, sid] + passthrough, cwd=ROOT, env=env)

    if "--dry-run" in args:
        print("[queue] dry-run なのでキューは変えない")
        write_status("dry-run", sid, len(q))
        return 0
    if r.returncode == 0:
        q.pop(0); save_queue(q)
        print(f"[queue] {sid} を投稿済みとして外した。残り {len(q)} 件")
        write_status("posted", sid, len(q))
        return 0
    print(f"[queue] {sid} の投稿に失敗（終了コード {r.returncode}）。キューに残す")
    write_status("failed", sid, len(q), f"post_new_spot.py exit={r.returncode}")
    return 1


if __name__ == "__main__":
    sys.exit(main())

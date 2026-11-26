"""
シーズン前の見直しの期間（2026-11-26・運営者と決定）。

紅葉・桜の名所は、混む時期だけの決まり（臨時の料金・臨時駐車場・入庫を断る・
交通規制・混む時の犬の扱い）が毎年出る。ふだんの見直しは約1か月で一巡するが、
回ってくる日がシーズンと関係ないため、発表の前に見て次はもう盛りの最中、
ということが起きる（嵐山の「繁忙期は自家用車の入庫を断ることがある」を見落とした）。

期間は「決まりが出始める頃」から「見頃の途中」まで（関西）:
  紅葉: 見頃 11月中旬〜12月上旬・発表 10月上旬〜11月上旬 → 10月1日〜11月20日
  桜  : 見頃 3月下旬〜4月上旬・発表 3月上旬〜中旬       → 3月1日〜4月5日

get_next_check_targets.py（対象の選び方）と build_codex_spot_prompt.py（Codexへの問い）の
両方がここを読む。期間を変える時はここだけ直す。
"""

import datetime

# (タグ, 呼び名, 始まり(月,日), 終わり(月,日))
SEASONS = [
    ("koyo", "紅葉", (10, 1), (11, 20)),
    ("sakura", "桜", (3, 1), (4, 5)),
]


def active_seasons(today):
    """今日が期間に入っている季節を返す。[{tag, label, start, end}]（start/end は date）"""
    out = []
    for tag, label, (sm, sd), (em, ed) in SEASONS:
        start = datetime.date(today.year, sm, sd)
        end = datetime.date(today.year, em, ed)
        if start <= today <= end:
            out.append({"tag": tag, "label": label, "start": start, "end": end})
    return out


def seasons_for_spot(spot, today):
    """そのスポットのタグに当てはまる、今日が期間中の季節"""
    tags = spot.get("tags") or []
    return [s for s in active_seasons(today) if s["tag"] in tags]


# 今年の発表がまだ見つからなかった名所（wait）を、もう一度見に行くまでの日数
RETRY_DAYS = 14


def season_key(s):
    """進捗ファイルの season_checks の鍵（例: 2027-koyo）"""
    return "{}-{}".format(s["start"].year, s["tag"])


def parse_day(v):
    """YYYY-MM-DD の文字列だけを日付にする。ほかの型・壊れた文字列は None"""
    if not isinstance(v, str):
        return None
    try:
        return datetime.date.fromisoformat(v)
    except ValueError:
        return None


def season_status(sid, s, today, season_checks, last_checked):
    """その季節の見直しの状態。
    done   … 今年の発表を確かめ終えた（その季節はもう割り込ませない）
    wait   … 見たが今年の発表がまだ無かった・調べきれなかった。RETRY_DAYS 後にまた割り込ませる
    unseen … 期間に入ってからまだ見ていない
    結果を書き忘れても、期間中に見た日（last_checked）があれば wait として扱う（毎回選び続けないため）
    戻り値: (状態, 最後に見た日 or None)
    """
    rec = {}
    if isinstance(season_checks, dict):
        r = season_checks.get(season_key(s))
        if isinstance(r, dict) and isinstance(r.get(sid), dict):
            rec = r[sid]
    seen = []
    d = parse_day(rec.get("date"))
    if d and s["start"] <= d <= today:
        seen.append(d)
    if isinstance(last_checked, dict):
        d2 = parse_day(last_checked.get(sid))
        if d2 and s["start"] <= d2 <= today:
            seen.append(d2)
    last = max(seen) if seen else None
    dd = parse_day(rec.get("date"))
    if rec.get("result") == "done" and dd and s["start"] <= dd <= today:
        return "done", last
    if last is None:
        return "unseen", None
    return "wait", last


def is_done(rec, s, today):
    """記録が「その季節の期間内・今日以前に済み」になっているか（更新側が済みを守る判定にも使う）"""
    if not isinstance(rec, dict) or rec.get("result") != "done":
        return False
    d = parse_day(rec.get("date"))
    return bool(d and s["start"] <= d <= today)


def season_note(s):
    """出力用の短い形"""
    return {
        "season": s["tag"],
        "label": s["label"],
        "window": "{}〜{}".format(s["start"].isoformat(), s["end"].isoformat()),
    }

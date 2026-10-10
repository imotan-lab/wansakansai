#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""spots.json の「表示すると誤情報になる状態」を機械で見つける（2026-09-28導入）。

なぜ要るか:
  2026-09-28、小目津公園（公式が園内の犬の散歩を禁止）で自動タスクが dogSize を全部 false にしたところ、
  表示側は「中型犬が不可なら小型犬のみ入場可」と出す作りだったため、犬が入れない公園に
  「小型犬のみ入場可（中型犬・大型犬は不可）」の札とタイトル「犬連れOK」が本番に出た。
  Codexの変更レビューは事実（散歩禁止）を確かめたが、値がどう表示されるかはサイトの決まりなので見られない。
  だから「この値の組み合わせは公開してはいけない」を機械で止める。

判定:
  NG1 dogSize が small/medium/large すべて false … 犬が入れない施設。掲載しないか、人が判断するまで公開しない
  NG2 small-dog-only タグと dogSize.medium=false が食い違う … フィルターと札が別のことを言う
  NG3 dogArea が outdoor-only / carry-only 以外の値
  NG4 dogRun.maxSize が small/medium/large 以外の値
  NG5 carryLabel があるのに dogArea が carry-only でない
  ── 2026-10-06追加（運営者の指摘を受けてCodexと確認しあった結果。今のデータでは0件のものだけを関所にした）──
  NG6 id が英小文字・数字・ハイフン以外／重複／index … ページのURLになる値
  NG7 lat/lng が数値でない・関西の範囲外 … 近い順の並べ替えと地図が壊れる
  NG8 toilet.available=false なのに toilet.western=true
  NG9 stay-only タグなのに visited が true でない … 「運営者が泊まった宿だけ載せる」決まりの表示と食い違う
  NG10 aliases に1文字以下・重複がある／同じ別名が別のスポットにもある … 危険情報が別のスポットに結び付く
       （2026-10-06に「かぶとやま」が京丹後のかぶと山公園と西宮の甲山森林公園の両方にあった）
  NG11 images / imageUrl のファイルが無い・imageUrl が images の1枚目と違う。
       パスは images/spots/ の下（フォルダ名がidと違う既存分あり: chikatsu-asuka）で、区切りは「/」、大文字小文字までファイルと一致すること
       （Windowsでは大文字小文字が違っても開けてしまうが、本番のサーバーでは404になる）
  NG12 tags が配列でない・決まった語以外・重複
  NG13 git HEAD にあったスポットの id が消えている … ページのURLが切れる。
       自動タスクはスポットを消さない。人が決めて対話セッションで消す時だけ --allow-removed を付ける
  NG14 lastChecked が YYYY-MM-DD でない・今日より先／visit が {date, note}（または配列）でない・visited が true でない
       （訪問メモは「運営者が訪れた」と書く欄なので、訪問済みマークと食い違わせない）
  ※ NG7 の範囲（緯度33.3〜35.9・経度134.2〜136.9）は今の掲載地域（近畿6府県）に合わせたもの。地域を広げる時はここも直す

使い方:
  python scripts/check_spot_data.py            … NGを一覧。NGがあれば終了コード1
  python scripts/check_spot_data.py --json     … {"ok": bool, "ngs": [...]}
スポット更新タスク（am/pm）は書き込み後・コミット前に必ず流し、NGならコミットしない。
"""
import collections
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPOTS = ROOT / "data" / "spots.json"
ID_RE = re.compile(r"[a-z0-9][a-z0-9-]*")
DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
import datetime as _dt
TODAY = f"{_dt.date.today():%Y-%m-%d}"
TAGS = {"sakura","koyo", "water", "rain", "small-dog-only", "stay-ok", "stay-only"}


def in_kansai(lat, lng) -> bool:
    return isinstance(lat, (int, float)) and 33.3 <= lat <= 35.9 and isinstance(lng, (int, float)) and 134.2 <= lng <= 136.9


def exact_file(rel: str) -> bool:
    """大文字小文字まで一致するファイルがあるか（Windowsの is_file は大文字小文字を区別しない）"""
    p = ROOT
    for part in rel.split("/"):
        try:
            names = {c.name for c in p.iterdir()}
        except (FileNotFoundError, NotADirectoryError):
            return False
        if part not in names:
            return False
        p = p / part
    return p.is_file()


def removed_ids(spots: list) -> list:
    import subprocess
    try:
        head = subprocess.run(["git", "show", "HEAD:data/spots.json"], cwd=ROOT, capture_output=True, timeout=30)
        before = {s.get("id") for s in json.loads(head.stdout.decode("utf-8"))}
    except Exception:
        return []
    return sorted(before - {s.get("id") for s in spots})


def check(spots: list) -> list:
    ngs = []
    owners = collections.defaultdict(set)
    for s in spots:
        for a in [s.get("name")] + list(s.get("aliases") or []):
            if isinstance(a, str):
                owners[a].add(s.get("id"))
    for k, v in collections.Counter(s.get("id") for s in spots).items():
        if v > 1:
            ngs.append(f"{k}: id が{v}件ある（ページのURLが重なる）")
    for s in spots:
        sid, name = s.get("id"), s.get("name")
        if not isinstance(sid, str) or not ID_RE.fullmatch(sid) or sid == "index":
            ngs.append(f"{sid!r}（{name}）: id は英小文字・数字・ハイフンだけで、index 以外にする")
        lat, lng = s.get("lat"), s.get("lng")
        if not in_kansai(lat, lng):
            ngs.append(f"{sid}（{name}）: lat/lng が数値でないか関西の範囲外（{lat}, {lng}）")
        pk = s.get("parking") or {}
        if ("lat" in pk or "lng" in pk) and not in_kansai(pk.get("lat"), pk.get("lng")):
            ngs.append(f"{sid}（{name}）: parking.lat/lng が数値でないか関西の範囲外（{pk.get('lat')}, {pk.get('lng')}）")
        tg = s.get("tags")
        if not isinstance(tg, list):
            ngs.append(f"{sid}（{name}）: tags が配列でない")
        else:
            bad = [t for t in tg if t not in TAGS]
            if bad:
                ngs.append(f"{sid}（{name}）: 決まった語以外のタグ {bad}（使える語: {', '.join(sorted(TAGS))}。増やす時は js/app.js の FILTER_GROUPS とここを一緒に直す）")
            if len(set(tg)) != len(tg):
                ngs.append(f"{sid}（{name}）: tags に同じ値が2回ある")
        t = s.get("toilet") or {}
        if t.get("available") is False and t.get("western") is True:
            ngs.append(f"{sid}（{name}）: トイレ無しなのに洋式になっている")
        if "stay-only" in (s.get("tags") or []) and s.get("visited") is not True:
            ngs.append(f"{sid}（{name}）: stay-only は運営者が泊まった宿だけ（visited=true が要る）")
        al = s.get("aliases") or []
        for a in al:
            if not isinstance(a, str) or len(a.strip()) <= 1:
                ngs.append(f"{sid}（{name}）: 短すぎる別名 {a!r}（危険情報が無関係に結び付く）")
            elif len(owners.get(a, ())) > 1:
                ngs.append(f"{sid}（{name}）: 別名『{a}』が別のスポット（{', '.join(sorted(x for x in owners[a] if x != sid))}）にもある")
        if len(set(al)) != len(al):
            ngs.append(f"{sid}（{name}）: aliases に同じ値が2回ある")
        imgs = s.get("images") or []
        for p in imgs + ([s["imageUrl"]] if s.get("imageUrl") else []):
            if not isinstance(p, str) or not p.startswith("images/spots/") or "\\" in p or ".." in p:
                ngs.append(f"{sid}（{name}）: 画像のパスは images/spots/ の下に「/」区切りで書く（今: {p!r}）")
            elif not exact_file(p):
                ngs.append(f"{sid}（{name}）: 画像ファイルが無いか、大文字小文字が違う {p}")
        lc = s.get("lastChecked")
        if lc is not None and (not isinstance(lc, str) or not DATE_RE.fullmatch(lc) or lc > TODAY):
            ngs.append(f"{sid}（{name}）: lastChecked は今日までの YYYY-MM-DD（今: {lc!r}）")
        if "visit" in s:
            vs = s["visit"] if isinstance(s["visit"], list) else [s["visit"]]
            for v in vs:
                if not isinstance(v, dict) or not isinstance(v.get("note"), str) or not v["note"].strip() \
                        or not isinstance(v.get("date"), str) or not DATE_RE.fullmatch(v["date"]) or v["date"] > TODAY:
                    ngs.append(f"{sid}（{name}）: visit は {{date: 今日までのYYYY-MM-DD, note: 本文}}（今: {v!r}）")
            if s.get("visited") is not True:
                ngs.append(f"{sid}（{name}）: 訪問メモ（visit）があるのに visited が true でない")
        if imgs and s.get("imageUrl") and s["imageUrl"] != imgs[0]:
            ngs.append(f"{sid}（{name}）: imageUrl が images の1枚目と違う")
        sid, name = s.get("id"), s.get("name")
        ds = s.get("dogSize") or {}
        tags = s.get("tags") or []
        if all(ds.get(k) is False for k in ("small", "medium", "large")):
            ngs.append(f"{sid}（{name}）: dogSize がすべて false＝犬が入れない施設。掲載しないか、公開前に人が判断する（そのまま公開すると誤表示になる）")
        if ("small-dog-only" in tags) != (ds.get("medium") is False):
            ngs.append(f"{sid}（{name}）: small-dog-only タグ（{'あり' if 'small-dog-only' in tags else 'なし'}）と dogSize.medium（{ds.get('medium')}）が食い違う")
        if s.get("dogArea") not in (None, "outdoor-only", "carry-only"):
            ngs.append(f"{sid}（{name}）: dogArea の値が想定外: {s.get('dogArea')!r}")
        if "carryLabel" in s and s.get("dogArea") != "carry-only":
            ngs.append(f"{sid}（{name}）: carryLabel は dogArea=carry-only の時だけ使う（今は {s.get('dogArea')!r}）")
        mx = (s.get("dogRun") or {}).get("maxSize")
        if mx not in (None, "small", "medium", "large"):
            ngs.append(f"{sid}（{name}）: dogRun.maxSize の値が想定外: {mx!r}")
    return ngs


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    spots = json.loads(SPOTS.read_text(encoding="utf-8"))
    ngs = check(spots)
    gone = removed_ids(spots)
    if gone and "--allow-removed" not in sys.argv:
        ngs.append(f"git HEAD にあったスポットが消えている: {', '.join(gone)}（ページのURLが切れる。人が決めて消す時だけ --allow-removed）")
    if "--json" in sys.argv:
        print(json.dumps({"ok": not ngs, "ngs": ngs}, ensure_ascii=False))
    else:
        print(f"=== スポットデータ点検: {len(spots)}件 / NG {len(ngs)}件 ===")
        for n in ngs:
            print("  NG:", n)
    return 1 if ngs else 0


if __name__ == "__main__":
    sys.exit(main())

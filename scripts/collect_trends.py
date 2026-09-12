"""Googleトレンドで季節語の「いつ探されるか」を取る（pytrends・非公式API）。

出力: C:/Users/imao_/Documents/wansakansai/research/trends_YYYY-MM-DD.json / .txt
  各語について直近24か月の週次の相対値（その語の最大=100）を月平均にし、
  山の月（上位3か月）を出す。語どうしの大小は比べられない（別スケール）ので、
  別途 anchor（犬連れ）と同時取得した相対値を "vs_anchor" に持つ。

失敗（429など）は語ごとに記録して先へ進む。粘らない。

★2026-09-12実測: 全語で「Google returned a response with code 400」。pytrends が Google 側の変更に
  追従できておらず、現時点では使えない。季節の山は一般的な見頃で補った。動くようになったら再利用する。
"""
import json, sys, time, datetime, os
sys.stdout.reconfigure(encoding="utf-8")
OUT_DIR = r"C:/Users/imao_/Documents/wansakansai/research"
TODAY = datetime.date.today().isoformat()
RAW = os.path.join(OUT_DIR, f"trends_{TODAY}.json")
TXT = os.path.join(OUT_DIR, f"trends_{TODAY}.txt")

TERMS = ["犬連れ 紅葉", "犬連れ コスモス", "犬連れ ハイキング", "犬 みかん狩り", "犬連れ イルミネーション",
         "犬連れ 梅", "犬連れ 温泉", "犬連れ 桜", "犬 いちご狩り", "犬連れ 芝桜", "犬連れ 藤", "犬連れ バラ",
         "犬 あじさい", "犬 水遊び", "犬 川遊び", "犬連れ 海", "犬 ひまわり", "犬連れ 高原", "犬連れ 室内",
         "ドッグラン", "犬連れ 公園", "犬連れ お出かけ", "犬連れ 関西", "犬連れ 大阪", "犬連れ 京都", "犬連れ 奈良",
         "犬連れ 滋賀", "犬連れ 和歌山", "犬連れ 兵庫", "犬連れ 淡路島", "犬連れ 白浜", "犬連れ 琵琶湖"]
ANCHOR = "犬連れ"

# pytrends は urllib3 v2 で method_whitelist を渡して落ちるので、受け取って allowed_methods に読み替える
import urllib3.util.retry as _retry
_orig_init = _retry.Retry.__init__
def _patched_init(self, *a, **kw):
    if "method_whitelist" in kw:
        kw["allowed_methods"] = kw.pop("method_whitelist")
    _orig_init(self, *a, **kw)
_retry.Retry.__init__ = _patched_init
from pytrends.request import TrendReq

def month_avg(df, col):
    m = df[col].groupby([df.index.year, df.index.month]).mean()
    return {f"{y}-{mo:02d}": round(float(v), 1) for (y, mo), v in m.items()}

def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    # retries/backoff_factor を渡すと urllib3 v2 で method_whitelist エラーになる（2026-09-12実測）
    pt = TrendReq(hl="ja-JP", tz=-540, timeout=(10, 30))
    out = {"date": TODAY, "timeframe": "today 24-m", "geo": "JP", "terms": {}, "vs_anchor": {}, "errors": {}}
    for i, t in enumerate(TERMS, 1):
        try:
            pt.build_payload([t], timeframe="today 24-m", geo="JP")
            df = pt.interest_over_time()
            if df.empty:
                out["errors"][t] = "empty"
            else:
                out["terms"][t] = month_avg(df, t)
            print(f"{i}/{len(TERMS)} {t}: {'ok' if t in out['terms'] else 'empty'}")
        except Exception as e:
            out["errors"][t] = str(e)[:200]
            print(f"{i}/{len(TERMS)} {t}: ERROR {str(e)[:120]}")
            if "429" in str(e):
                time.sleep(30)
        json.dump(out, open(RAW, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        time.sleep(6)
    # anchor と同時取得（4語ずつ＋anchor）で語どうしの大小を見る
    rest = [t for t in TERMS if t in out["terms"]]
    for k in range(0, len(rest), 4):
        grp = [ANCHOR] + rest[k:k+4]
        try:
            pt.build_payload(grp, timeframe="today 12-m", geo="JP")
            df = pt.interest_over_time()
            if not df.empty:
                for t in grp:
                    out["vs_anchor"][t] = round(float(df[t].mean()), 1)
            print(f"anchor group {k//4+1}: ok")
        except Exception as e:
            out["errors"][f"anchor{k}"] = str(e)[:200]
            print(f"anchor group {k//4+1}: ERROR {str(e)[:120]}")
            if "429" in str(e):
                time.sleep(30)
        json.dump(out, open(RAW, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        time.sleep(6)
    # 要約
    lines = [f"# Googleトレンド {TODAY}（geo=JP・直近24か月の月平均・各語の最大=100）", ""]
    for t, mm in out["terms"].items():
        top = sorted(mm.items(), key=lambda x: -x[1])[:4]
        # 月番号ごとに平均（2年分をまとめる）
        bym = {}
        for ym, v in mm.items():
            bym.setdefault(ym[5:], []).append(v)
        prof = " ".join(f"{m}:{sum(v)/len(v):.0f}" for m, v in sorted(bym.items()))
        va = out["vs_anchor"].get(t)
        lines.append(f"- {t}  山={', '.join(f'{ym}({v})' for ym, v in top)}  vs犬連れ={va}")
        lines.append(f"    月別: {prof}")
    if out["errors"]:
        lines.append("")
        lines.append("## 取れなかった語")
        for t, e in out["errors"].items():
            lines.append(f"- {t}: {e}")
    open(TXT, "w", encoding="utf-8").write("\n".join(lines))
    print(f"-> {TXT}")

if __name__ == "__main__":
    main()

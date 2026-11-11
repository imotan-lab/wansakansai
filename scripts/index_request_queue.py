"""Search Console の「インデックス登録をリクエスト」を1日10件ずつ進めるための台帳（2026-11-11 運営者「毎日10件ずつタスクに入れよう」）

インデックスに登録されていないページは Google の検索に一切出ない。Search Console の登録リクエストは1日10件ほどが上限なので、
未登録のページを優先順に並べた台帳を持ち、毎日の自動タスク（wansakansai-spot-update-am の STEP 10.5）が先頭から10件ずつ頼む。

台帳はリポジトリの外: C:/Users/imao_/Documents/wansakansai/index_request_queue.json
ログ: C:/Users/imao_/.claude/logs/wansakansai_index_request_YYYY-MM-DD.log

使い方:
  python scripts/index_request_queue.py --seed ファイル   # 未登録のURL（1行1つ・相対でも可）を台帳に足す（既にあるものは足さない）
  python scripts/index_request_queue.py --next 10         # 今日頼む分を出す（JSON）。頼んでから RETRY_DAYS 日たっていないもの・登録済みは出さない
  python scripts/index_request_queue.py --mark URL --result requested|indexed|quota|error|gone [--note 文]
  python scripts/index_request_queue.py --status          # 件数のまとめ
  python scripts/index_request_queue.py --selftest        # 台帳を使わずに動きを確かめる

結果の意味:
  requested = 頼めた（「インデックス登録をリクエスト済み」が出た）
  indexed   = URL検査で「URL は Google に登録されています」だった（頼まない・台帳から卒業）
  quota     = 「割り当てを超えました」が出た（その日はそこで止める。この URL は翌日また出る）
  error     = 頼めなかった（画面が出ない・ボタンが無い等）。3回続いたら出さない（人が見る）
  gone      = ページが無くなった・noindex にした（台帳から外す）
"""
import argparse
import datetime as dt
import json
import os
import sys
import tempfile

sys.stdout.reconfigure(encoding='utf-8')

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QUEUE = r'C:/Users/imao_/Documents/wansakansai/index_request_queue.json'
DEMAND = r'C:/Users/imao_/Documents/wansakansai/spot_demand.json'
LOGDIR = r'C:/Users/imao_/.claude/logs'
SITE = 'https://wansakansai.com/'
RETRY_DAYS = 28      # 頼んでも登録されなかったページは、4週間たったらもう一度頼む
MAX_ERRORS = 3

# 先に頼むもの: スポットへの入口になるページ（ここが登録されると、Google が残りのスポットを見つけやすくなる）
HUBS = ['spots/index.html', 'themes/index.html', 'themes/dogrun-free.html', 'themes/dogrun.html',
        'themes/sakura.html', 'themes/koyo.html', 'themes/water.html', 'themes/rain.html', 'themes/free.html',
        'blog/index.html', 'editorial.html']


def now():
    return dt.datetime.now()


def log(msg):
    os.makedirs(LOGDIR, exist_ok=True)
    line = f'[{now():%Y/%m/%d %H:%M:%S}] {msg}'
    with open(os.path.join(LOGDIR, f'wansakansai_index_request_{now():%Y-%m-%d}.log'), 'a', encoding='utf-8') as f:
        f.write(line + '\n')


def norm(u):
    u = u.strip()
    if not u:
        return ''
    if not u.startswith('http'):
        u = SITE + u.lstrip('/')
    return u.split('#')[0]


def load(path=QUEUE):
    if not os.path.exists(path):
        return {'items': {}}
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def save(d, path=QUEUE):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), suffix='.tmp')
    with os.fdopen(fd, 'w', encoding='utf-8') as f:
        json.dump(d, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def priority(url, demand, photos):
    """小さいほど先。入口のページ → 検索で見られているスポット → 写真のあるスポット → 残り"""
    rel = url[len(SITE):] if url.startswith(SITE) else url
    if rel in HUBS:
        return (0, HUBS.index(rel), 0)
    if rel.startswith('spots/') and rel.endswith('.html'):
        sid = rel[len('spots/'):-len('.html')]
        imp = demand.get(sid, {}).get('impressions', 0)
        if imp:
            return (1, -imp, 0)
        if sid in photos:
            return (2, 0, 0)
        return (3, 0, 0)
    if rel.startswith('blog/'):
        return (2, 0, 0)
    return (4, 0, 0)


def site_facts():
    demand, photos, ids = {}, set(), set()
    try:
        with open(DEMAND, encoding='utf-8') as f:
            demand = json.load(f).get('spots', {})
    except Exception as e:  # 需要が読めなくても台帳は回す
        log(f'[WARN] 需要ファイルを読めない: {e}')
    try:
        with open(os.path.join(ROOT, 'data', 'spots.json'), encoding='utf-8') as f:
            spots = json.load(f)
        for s in spots:
            ids.add(s['id'])
            if s.get('images'):
                photos.add(s['id'])
    except Exception as e:
        log(f'[WARN] spots.json を読めない: {e}')
    return demand, photos, ids


def exists_on_site(url, ids):
    rel = url[len(SITE):] if url.startswith(SITE) else url
    if rel.startswith('spots/') and rel.endswith('.html') and rel != 'spots/index.html':
        return rel[len('spots/'):-len('.html')] in ids
    return os.path.exists(os.path.join(ROOT, rel.replace('/', os.sep)))


def cmd_seed(path, d):
    with open(path, encoding='utf-8') as f:
        urls = [norm(x) for x in f.read().split()]
    added = 0
    for u in urls:
        if u and '?' not in u and u not in d['items']:
            d['items'][u] = {'added': f'{now():%Y-%m-%d}', 'history': []}
            added += 1
    log(f'seed: {len(urls)}件を読み、{added}件を台帳に足した（合計{len(d["items"])}件）')
    print(f'added {added} / total {len(d["items"])}')
    return d


def due(item, today):
    hist = item.get('history', [])
    if any(h['result'] in ('indexed', 'gone') for h in hist):
        return False
    errs = 0
    for h in reversed(hist):
        if h['result'] == 'error':
            errs += 1
        else:
            break
    if errs >= MAX_ERRORS:
        return False
    last_req = [h for h in hist if h['result'] == 'requested']
    if last_req:
        last = dt.date.fromisoformat(last_req[-1]['date'][:10])
        if (today - last).days < RETRY_DAYS:
            return False
    if any(h['result'] == 'quota' and h['date'][:10] == today.isoformat() for h in hist):
        return False
    return True


def cmd_next(n, d, today=None):
    today = today or now().date()
    demand, photos, ids = site_facts()
    cands = []
    for u, item in d['items'].items():
        if not due(item, today):
            continue
        if ids and not exists_on_site(u, ids):
            item.setdefault('history', []).append({'date': f'{now():%Y-%m-%dT%H:%M}', 'result': 'gone', 'note': 'サイトに無い（消したページ）'})
            log(f'gone: {u}（サイトに無いので台帳から外した）')
            continue
        cands.append((priority(u, demand, photos), u))
    cands.sort()
    out = [u for _, u in cands[:n]]
    log(f'next: {len(cands)}件が対象、今日は{len(out)}件: ' + ' '.join(x[len(SITE):] for x in out))
    print(json.dumps({'today': out, 'remaining': len(cands)}, ensure_ascii=False))
    return d


def cmd_mark(url, result, note, d):
    u = norm(url)
    if u not in d['items']:
        d['items'][u] = {'added': f'{now():%Y-%m-%d}', 'history': []}
    d['items'][u].setdefault('history', []).append({'date': f'{now():%Y-%m-%dT%H:%M}', 'result': result, 'note': note or ''})
    log(f'mark: {u[len(SITE):]} → {result}' + (f'（{note}）' if note else ''))
    print('ok')
    return d


def summary(d, today=None):
    today = today or now().date()
    c = {'indexed': 0, 'gone': 0, 'requested_waiting': 0, 'error_stopped': 0, 'due': 0}
    for u, item in d['items'].items():
        hist = item.get('history', [])
        res = [h['result'] for h in hist]
        if 'indexed' in res:
            c['indexed'] += 1
        elif 'gone' in res:
            c['gone'] += 1
        elif due(item, today):
            c['due'] += 1
        elif res and res[-1] == 'error':
            c['error_stopped'] += 1
        else:
            c['requested_waiting'] += 1
    c['total'] = len(d['items'])
    return c


def selftest():
    import shutil
    tmpd = tempfile.mkdtemp()
    p = os.path.join(tmpd, 'q.json')
    seed = os.path.join(tmpd, 'seed.txt')
    with open(seed, 'w', encoding='utf-8') as f:
        f.write('spots/index.html\nspots/aaa.html\nspots/bbb.html\nhttps://wansakansai.com/spot.html?id=x\n')
    d = cmd_seed(seed, {'items': {}})
    assert len(d['items']) == 3, d  # ? 付きは足さない
    today = dt.date(2026, 11, 11)
    it = d['items']['https://wansakansai.com/spots/aaa.html']
    it['history'].append({'date': '2026-11-11T12:00', 'result': 'requested'})
    assert not due(it, today) and not due(it, today + dt.timedelta(days=27)) and due(it, today + dt.timedelta(days=28))
    it2 = d['items']['https://wansakansai.com/spots/bbb.html']
    it2['history'] += [{'date': '2026-11-11T12:00', 'result': 'error'}] * 3
    assert not due(it2, today)
    it3 = d['items']['https://wansakansai.com/spots/index.html']
    it3['history'].append({'date': '2026-11-11T12:00', 'result': 'quota'})
    assert not due(it3, today) and due(it3, today + dt.timedelta(days=1))
    it3['history'].append({'date': '2026-11-12T12:00', 'result': 'indexed'})
    assert not due(it3, today + dt.timedelta(days=60))
    assert priority('https://wansakansai.com/spots/index.html', {}, set())[0] == 0
    assert priority('https://wansakansai.com/spots/x.html', {'x': {'impressions': 5}}, set()) < priority('https://wansakansai.com/spots/y.html', {}, {'y'})
    shutil.rmtree(tmpd)
    print('selftest ok')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--seed')
    ap.add_argument('--next', type=int)
    ap.add_argument('--mark')
    ap.add_argument('--result', choices=['requested', 'indexed', 'quota', 'error', 'gone'])
    ap.add_argument('--note', default='')
    ap.add_argument('--status', action='store_true')
    ap.add_argument('--selftest', action='store_true')
    a = ap.parse_args()
    if a.selftest:
        selftest()
        return 0
    try:
        d = load()
        if a.seed:
            d = cmd_seed(a.seed, d); save(d)
        elif a.next is not None:
            d = cmd_next(a.next, d); save(d)
        elif a.mark:
            if not a.result:
                print('--result が要る'); return 2
            d = cmd_mark(a.mark, a.result, a.note, d); save(d)
        elif a.status:
            s = summary(d)
            log(f'status: {s}')
            print(json.dumps(s, ensure_ascii=False))
        else:
            ap.print_help(); return 2
        return 0
    except Exception as e:
        log(f'[ERROR] {type(e).__name__}: {e}')
        print(f'[ERROR] {e}')
        return 1


if __name__ == '__main__':
    sys.exit(main())

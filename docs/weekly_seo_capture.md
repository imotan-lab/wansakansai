# 週次レポートの数字の取り方（Search Console・GA4）

週次SEOタスク（wansakansai-weekly-seo）の STEP 1b・1c で使う。2026-10-20 に実機で動かして、手で取った値と一致することを確かめた。

- 開くURLは `python scripts/seo_week_dates.py --csv C:/Users/imao_/Documents/wansakansai/seo_daily.csv` が出す。**日付を自分で計算しない**
- 下のJSは `javascript_tool` にそのまま渡す。**返ってきた文字列を加工せずに**、Writeツールで指定のファイルに書く
- 表は10行ずつしか見えないが、ページの中には全行が入っている（行数の変更は要らない）
- 一度に返せる文字数に限りがあるので、出力は小分けにしてある。末尾が `[TRUNCATED]` なら、そのJSの `slice` を半分にして2回に分ける
- 前の週の表は `sessionStorage` に置いてから今週の表で突き合わせる（同じタブで続けて開くこと。別のタブだと消える）

## Search Console：検索語句

1) `gsc_query_prev` を開き、次を実行（前の週の全行を保存）:
```js
await new Promise(r=>setTimeout(r,6000)); const n=s=>+s.replace(/,/g,''); const q=[...document.querySelectorAll('tr')].map(tr=>[...tr.querySelectorAll('td')].map(td=>td.innerText.trim())).filter(r=>r.length>=5&&/^[\d,]+$/.test(r[1]||'')).map(r=>[r[0],n(r[1]),n(r[2])]); sessionStorage.setItem('wk_qprev',JSON.stringify(q)); 'prev_rows='+q.length
```

2) 同じタブで `gsc_query_this` を開き、次を実行:
```js
await new Promise(r=>setTimeout(r,6000)); const n=s=>+s.replace(/,/g,''); const q=[...document.querySelectorAll('tr')].map(tr=>[...tr.querySelectorAll('td')].map(td=>td.innerText.trim())).filter(r=>r.length>=5&&/^[\d,]+$/.test(r[1]||'')).map(r=>[r[0],n(r[1]),n(r[2]),+r[4]]); const pv=Object.fromEntries(JSON.parse(sessionStorage.getItem('wk_qprev')||'[]').map(r=>[r[0],r[2]])); const P=s=>(s in pv)?pv[s]:null; window.__wq={screen_clicks:n((document.body.innerText.match(/合計クリック数\s*([\d,]+)/)||[,'0'])[1]), rows:q.length, prev_rows:Object.keys(pv).length, known_clicks:q.reduce((a,r)=>a+r[1],0), top:[...q].sort((a,b)=>b[1]-a[1]||b[2]-a[2]).slice(0,12).map(r=>[r[0],r[1],r[2],r[3],P(r[0])]), noclick:q.filter(r=>r[1]===0).sort((a,b)=>b[2]-a[2]).slice(0,8).map(r=>[r[0],r[2],r[3]]), grow:q.map(r=>[r[0],P(r[0]),r[2],r[1]]).filter(r=>r[2]-(r[1]||0)>=20).sort((a,b)=>(b[2]-(b[1]||0))-(a[2]-(a[1]||0))).slice(0,10)}; JSON.stringify({screen_clicks:__wq.screen_clicks,rows:__wq.rows,prev_rows:__wq.prev_rows,known_clicks:__wq.known_clicks})
```
続けて `JSON.stringify(__wq.top)`・`JSON.stringify(__wq.noclick)`・`JSON.stringify(__wq.grow)` を1つずつ実行する。
4つの返り値を、次の形でそのまま `C:/Users/imao_/.claude/logs/wansakansai_seo_queries_${DATE}.json` に書く:
`{"summary": （1つ目）, "top": （2つ目）, "noclick": （3つ目）, "grow": （4つ目）}`

- `top` は [語句, クリック, 表示, 平均順位, 前の週の表示（前の週の表に無ければ null）]
- 前の週の表は最大1,000行。null は「前の週の表に無い」＝少なかった（0とは限らない）

## Search Console：ページ

3) 同じタブで `gsc_page_prev` を開き、次を実行:
```js
await new Promise(r=>setTimeout(r,6000)); const n=s=>+s.replace(/,/g,''); const id=t=>{const m=t.match(/wansakansai\.com\/([^\s]*?)(\.html)?(\s|$)/); return ((m&&m[1])||'top').replace('spots/','')}; const p=[...document.querySelectorAll('tr')].map(tr=>[...tr.querySelectorAll('td')].map(td=>td.innerText.trim())).filter(r=>r.length>=5&&/wansakansai\.com/.test(r[0])).map(r=>[id(r[0]),n(r[1]),n(r[2])]); sessionStorage.setItem('wk_pprev',JSON.stringify(p)); 'prev_pages='+p.length
```

4) 同じタブで `gsc_page_this` を開き、次を実行:
```js
await new Promise(r=>setTimeout(r,6000)); const n=s=>+s.replace(/,/g,''); const id=t=>{const m=t.match(/wansakansai\.com\/([^\s]*?)(\.html)?(\s|$)/); return ((m&&m[1])||'top').replace('spots/','')}; const c=[...document.querySelectorAll('tr')].map(tr=>[...tr.querySelectorAll('td')].map(td=>td.innerText.trim())).filter(r=>r.length>=5&&/wansakansai\.com/.test(r[0])).map(r=>[id(r[0]),n(r[1]),n(r[2])]); const pv=Object.fromEntries(JSON.parse(sessionStorage.getItem('wk_pprev')||'[]').map(r=>[r[0],[r[1],r[2]]])); const cm=Object.fromEntries(c.map(r=>[r[0],[r[1],r[2]]])); window.__wp={rows:c.length, prev_rows:Object.keys(pv).length, top:[...c].sort((a,b)=>b[1]-a[1]).slice(0,15), up:c.map(r=>[r[0],pv[r[0]]?pv[r[0]][0]:0,r[1]]).filter(r=>r[2]-r[1]>=5&&r[2]>=2*r[1]).sort((a,b)=>(b[2]-b[1])-(a[2]-a[1])).slice(0,8), down:Object.keys(pv).map(k=>[k,pv[k][0],cm[k]?cm[k][0]:0]).filter(r=>r[1]>=5&&r[1]-r[2]>=4&&r[2]<=r[1]*0.6).sort((a,b)=>(b[1]-b[2])-(a[1]-a[2])).slice(0,8), new:c.filter(r=>!pv[r[0]]).sort((a,b)=>b[2]-a[2]).slice(0,10)}; JSON.stringify({rows:__wp.rows,prev_rows:__wp.prev_rows,up:__wp.up,down:__wp.down})
```
続けて `JSON.stringify(__wp.top)`・`JSON.stringify(__wp.new)` を実行する。

5) 同じタブで `gsc_page_last28` を開き、次を実行:
```js
await new Promise(r=>setTimeout(r,6000)); const n=s=>+s.replace(/,/g,''); const id=t=>{const m=t.match(/wansakansai\.com\/([^\s]*?)(\.html)?(\s|$)/); return ((m&&m[1])||'top').replace('spots/','')}; JSON.stringify([...document.querySelectorAll('tr')].map(tr=>[...tr.querySelectorAll('td')].map(td=>td.innerText.trim())).filter(r=>r.length>=5&&/wansakansai\.com/.test(r[0])).map(r=>[id(r[0]),n(r[1])]).sort((a,b)=>b[1]-a[1]).slice(0,40))
```
4つの返り値を、次の形でそのまま `C:/Users/imao_/.claude/logs/wansakansai_seo_pages_${DATE}.json` に書く:
`{"summary": （4の1つ目）, "top": （4の2つ目）, "new": （4の3つ目）, "last28": （5）}`

- id は `spots/` を外したスポットID。`top` はトップページ、`index` は全スポット一覧、`themes/…` はテーマ別
- `up` = 前の週より5回以上かつ2倍以上に増えた／`down` = 前の週5回以上で、4回以上かつ4割以上減った／`new` = 前の週の表に無かったページ（前の週に表示0回。初めてGoogleに載った意味ではない）

## GA4

各URLを開いて10秒待ち、次のJSを実行する（4つとも同じJS）。**返り値の `period` に今週の日付（例「10月5日～2026年10月11日」）が入っていることを確かめる**（違えばURLの日付が効いていない）:
```js
await new Promise(r=>setTimeout(r,10000)); const rows=[...document.querySelectorAll('tr')].map(tr=>[...tr.querySelectorAll('td,th')].map(td=>td.innerText.replace(/\s+/g,' ').trim()).filter(x=>x)); const num=s=>+String(s).split(' ')[0].replace(/[,¥]/g,''); const out={period:(rows.find(r=>/～\d{4}年/.test(r[0]||''))||[''])[0], total:null, rows:{}}; let cur=null; for(const r of rows){ const k=r.indexOf('合計'); if(k>=0&&r[k+1]){ const p=r[k+1].split(' '); out.total=[num(p[0]),num(p[1])]; } else if(/^\d+$/.test(r[0])&&r.length===2){ cur=r[1]; out.rows[cur]=[]; } else if(cur&&/～\d{4}年/.test(r[0])&&out.rows[cur].length<2){ out.rows[cur].push([num(r[1]),num(r[2])]); } } JSON.stringify(out)
```
返り値を、次の形でそのまま `C:/Users/imao_/.claude/logs/wansakansai_seo_ga4_${DATE}.json` に書く:
`{"users": （ga4_users）, "channels": （ga4_channels）, "sources": （ga4_sources）, "events": （ga4_events）}`

- `rows[名前] = [[今週の1列目, 今週の2列目], [前の週の1列目, 前の週の2列目]]`
- `total` は合計の行の **[今週, 前の週]**（users なら総ユーザー数の今週と前の週。channels なら総セッション数）
- users の rows: 1列目＝総ユーザー数・2列目＝新規ユーザー数／channels・sources: 1列目＝セッション／events: 1列目＝イベント数・2列目＝そのイベントのユーザー数
- GA4のプロパティは表示名「犬阪んさい」（アカウント「うちどころ」の下・`a388917488p530354793`）

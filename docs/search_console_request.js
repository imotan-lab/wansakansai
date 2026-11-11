// Search Console の「URL 検査 → インデックス登録をリクエスト」を順に行う道具（2026-11-11）
// 使い方（wansakansai-spot-update-am の STEP 10.5）:
//   1) Search Console のページ（例: https://search.google.com/search-console/index?resource_id=https%3A%2F%2Fwansakansai.com%2F）
//      を開いたタブで、このファイルの中身をそのまま javascript_tool に渡す（window.__req と window.__run を定義するだけ）
//   2) javascript_tool で  window.__run([URL, URL, ...])  を呼ぶ（すぐ 'started N' が返る）
//   3) 1分おきに  JSON.stringify({busy: window.__busy, res: window.__res})  で様子を見る。busy が false になったら終わり
// 1件に1〜2分かかる（Google が公開URLを試すため）。javascript_tool は45秒で切れるので、1回の呼び出しで待ち切ろうとしないこと
// （切れてもページの中では動き続ける。2026-11-11 に実際に切れた）。
// 結果（res の各要素は [URL, 結果]）:
//   INDEXED            … 「URL は Google に登録されています」。頼まない（台帳は indexed）
//   REQUESTED          … 「インデックス登録をリクエスト済み」の小窓が新しく出た（台帳は requested）
//   QUOTA              … 「割り当て」を超えた。そこで止まる（台帳は quota・翌日また出る）
//   ERROR:理由         … 頼めなかった（台帳は error・理由を note に）
// PC がロック中でも動くように、キー入力やクリックの道具は使わず、ページの中の JavaScript だけで操作する。
// ★前の件の「リクエスト済み」の小窓を見て、次の件も済んだと読み違えないこと★（2026-11-11 に一度読み違えた）。
//   だから小窓は毎回閉じ、押す前と後で「リクエスト済み」の数が増えたかで判定している。
window.__req = async (TARGET) => {
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const text = () => document.body.innerText;
  const count = (s, w) => s.split(w).length - 1;
  const DONE = 'インデックス登録をリクエスト済み';

  // 1) 前の結果の小窓を閉じる
  document.querySelectorAll('[role="dialog"] [role="button"], [role="dialog"] button').forEach((b) => {
    if (/表示しない|閉じる|^OK$/.test(b.textContent.trim())) b.click();
  });
  await sleep(700);

  // 2) 上の検査欄に URL を入れて Enter
  const inp = [...document.querySelectorAll('input')].find((i) => /URL を検査/.test(i.getAttribute('aria-label') || i.placeholder || ''));
  if (!inp) return 'ERROR:検査欄が見つからない';
  inp.focus();
  Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(inp, TARGET);
  inp.dispatchEvent(new Event('input', { bubbles: true }));
  inp.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', code: 'Enter', keyCode: 13, which: 13, bubbles: true }));

  // 3) この URL の検査結果が出るまで待つ（ページの上に URL、その下に「URL 検査」が並ぶ）
  let st = '';
  for (let i = 0; i < 120; i++) {
    const t = text();
    if (t.includes(TARGET + '\nURL 検査')) {
      const m = t.match(/URL (?:が|は) Google に登録されて(?:いません|います)/);
      if (m) { st = m[0]; break; }
    }
    await sleep(500);
  }
  if (!st) return 'ERROR:検査結果が出ない';
  if (/登録されています/.test(st)) return 'INDEXED';

  // 4) 「インデックス登録をリクエスト」を押す
  const btn = [...document.querySelectorAll('[role="button"], button')].find((b) => b.textContent.includes('インデックス登録をリクエスト') && b.offsetParent !== null);
  if (!btn) return 'ERROR:リクエストのボタンが無い';
  const before = count(text(), DONE);
  btn.click();

  // 5) 結果の小窓を待つ（最大3分）
  for (let i = 0; i < 360; i++) {
    const t = text();
    if (count(t, DONE) > before) return 'REQUESTED';
    if (/割り当てを超え|割り当て量を超え|Quota exceeded/i.test(t)) return 'QUOTA';
    const err = t.match(/問題が発生しました[^\n]*/);
    if (err) return 'ERROR:' + err[0].slice(0, 60);
    await sleep(500);
  }
  return 'ERROR:3分待っても結果が出ない';
};

window.__run = (urls) => {
  window.__res = [];
  window.__busy = true;
  (async () => {
    for (const u of urls) {
      let r;
      try { r = await window.__req(u); } catch (e) { r = 'ERROR:' + String(e).slice(0, 60); }
      window.__res.push([u, r]);
      if (r === 'QUOTA') break;
    }
    window.__busy = false;
  })();
  return 'started ' + urls.length;
};
'defined';

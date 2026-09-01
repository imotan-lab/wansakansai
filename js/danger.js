// 全文を段落に分ける。descriptionは改行なしの一続きなので、句点で区切って
// 110字を目安にまとめる。文の途中では切らない
// 各段落は中でescapeHtmlを通しているため、呼び出し側はそのまま埋め込んでよい
function paragraphize(text) {
  const sentences = String(text || '').split('。').map(s => s.trim()).filter(Boolean);
  if (sentences.length === 0) return '';
  const paras = [];
  let buf = '';
  for (const s of sentences) {
    buf += s + '。';
    if (buf.length >= 110) { paras.push(buf); buf = ''; }
  }
  if (buf) {
    // 最後が短すぎる場合は前の段落にくっつける（1行だけの段落を作らない）
    if (paras.length > 0 && buf.length < 40) paras[paras.length - 1] += buf;
    else paras.push(buf);
  }
  return paras.map(p => '<p class="danger-card-desc">' + escapeHtml(p) + '</p>').join('');
}

// 一覧は要約だけ見せる。summaryが無いエントリは説明文の冒頭2文までを代わりに使う
// （自動更新タスクが要約を付け忘れても表示が壊れないようにするため）
function summaryOf(d) {
  if (d.summary) return d.summary;
  const text = (d.description || '').trim();
  const parts = text.split('。').filter(Boolean);
  let out = '';
  for (const p of parts) {
    if (out.length + p.length > 70) break;
    out += p + '。';
  }
  return out || text.slice(0, 70);
}

// ===== Danger Page =====

(async function () {
  renderHeader('danger');
  renderFooter();

  const container = document.getElementById('dangerList');

  try {
    const [dangers, spots] = await Promise.all([
      loadJSON('data/dangers.json'),
      loadJSON('data/spots.json')
    ]);

    if (dangers.length === 0) {
      container.innerHTML = `
        <div class="danger-empty">
          <p>現在、報告されている危険情報はありません。</p>
          <p style="margin-top:8px;font-size:0.85rem;">危険な情報を見かけた場合は、お問い合わせページからご報告ください。</p>
        </div>
      `;
      return;
    }

    // Find matching spots for a danger entry
    function findRelatedSpots(danger) {
      const text = danger.location + danger.description;
      return spots.filter(s => spotNameMatchesText(s, text));
    }

    // Sort by date descending
    dangers.sort((a, b) => new Date(b.date) - new Date(a.date));

    container.innerHTML = dangers.map(d => {
      const dateStr = new Date(d.date).toLocaleDateString('ja-JP', {
        year: 'numeric', month: 'long'
      });
      const related = findRelatedSpots(d);
      const linksHtml = related.length > 0
        ? `<div class="danger-card-links">${related.map(s =>
            `<a href="spots/${encodeURIComponent(s.id)}.html" class="danger-spot-link">${escapeHtml(s.name)}</a>`
          ).join('')}</div>`
        : '';
      return `
        <div class="danger-card">
          <p class="danger-card-date">${escapeHtml(dateStr)}</p>
          <p class="danger-card-location">${escapeHtml(d.location)}</p>
          <span class="danger-card-type">${escapeHtml(d.type)}</span>
          <p class="danger-card-summary">${escapeHtml(summaryOf(d))}</p>
          <details class="danger-detail">
            <summary>詳しく見る</summary>
            ${paragraphize(d.description)}
          </details>
          ${linksHtml}
        </div>
      `;
    }).join('');
  } catch (e) {
    container.innerHTML = '<div class="danger-empty"><p>データの読み込みに失敗しました</p></div>';
  }
})();

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

// ===== 季節の注意（毎年同じ時期に来るもの・2026-11-25） =====
// 日付で追いかける危険情報とは別に、data/seasonal_notes.json を常に出す。
// いまの月を含むものを上に、ほかは「ほかの時期の注意」に畳む。
// 1〜12の整数だけにそろえ、重複を除く（表示と「いまの時期か」の判定で同じものを使う）
function normMonths(months) {
  if (!Array.isArray(months)) return [];
  // 数か、数字だけの文字列だけを月として扱う（true や配列・オブジェクトは捨てる）
  const ok = months.filter(v => typeof v === 'number' || (typeof v === 'string' && /^\d{1,2}$/.test(v)));
  return [...new Set(ok.map(Number).filter(m => Number.isInteger(m) && m >= 1 && m <= 12))];
}

function monthsLabel(months) {
  const ms = normMonths(months);
  if (ms.length >= 12) return '通年';
  if (ms.length === 0) return '';
  const set = new Set(ms);
  // 年をまたぐ範囲（10〜2月など）も1つにまとめる。並びの始まり＝前の月が無い月
  const starts = ms.filter(m => !set.has(m === 1 ? 12 : m - 1));
  return starts.map(st => {
    let end = st;
    while (set.has(end === 12 ? 1 : end + 1) && (end === 12 ? 1 : end + 1) !== st) end = end === 12 ? 1 : end + 1;
    return st === end ? `${st}月` : `${st}〜${end}月`;
  }).join('・');
}

async function renderSeasonNotes() {
  const box = document.getElementById('seasonNotes');
  if (!box) return;
  let notes;
  try { notes = await loadJSON('data/seasonal_notes.json'); } catch (e) { return; }
  if (!Array.isArray(notes)) return;
  notes = notes.filter(n => n && typeof n.title === 'string' && typeof n.text === 'string');
  if (notes.length === 0) return;
  const m = new Date().getMonth() + 1;
  const inSeason = n => normMonths(n.months).includes(m);
  const card = n => `
    <div class="season-note">
      <p class="season-note-head"><span class="season-note-title">${escapeHtml(n.title)}</span><span class="season-note-months">${escapeHtml(monthsLabel(n.months))}</span></p>
      <p class="season-note-text">${escapeHtml(n.text)}</p>
    </div>`;
  const now = notes.filter(inSeason);
  const other = notes.filter(n => !inSeason(n));
  document.getElementById('seasonNotesNow').innerHTML = now.map(card).join('');
  if (other.length) {
    document.getElementById('seasonNotesOther').innerHTML = other.map(card).join('');
    document.getElementById('seasonNotesMore').hidden = false;
  }
  box.hidden = false;
}

// ===== Danger Page =====

(async function () {
  renderHeader('danger');
  renderFooter();

  const container = document.getElementById('dangerList');
  renderSeasonNotes();

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
      return spotsMatchingText(spots, text);
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

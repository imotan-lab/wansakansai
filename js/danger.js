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
            `<a href="spot.html?id=${s.id}" class="danger-spot-link">${s.name}</a>`
          ).join('')}</div>`
        : '';
      return `
        <div class="danger-card">
          <p class="danger-card-date">${dateStr}</p>
          <p class="danger-card-location">${d.location}</p>
          <span class="danger-card-type">${d.type}</span>
          <p class="danger-card-desc">${d.description}</p>
          ${linksHtml}
        </div>
      `;
    }).join('');
  } catch (e) {
    container.innerHTML = '<div class="danger-empty"><p>データの読み込みに失敗しました</p></div>';
  }
})();

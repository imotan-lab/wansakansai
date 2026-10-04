// ===== テーマ別まとめページ =====
// スポットの一覧と件数は generate_theme_pages.py が生HTMLに書き込む（2026-10-04）。
// 以前はここで spots.json を読んで一覧を描いていたが、Googleが読む最初のHTMLに一覧が無く、
// 検索の表示回数が0だったため静的生成に切り替えた。ここではヘッダーとフッターだけを描く。
renderHeader('themes');
renderFooter();

# X（Twitter）自動投稿の実装詳細

犬阪んさい（@wansakansai）のX自動投稿の詳細実装メモ。CLAUDE.mdから分離。

---

## 危険情報のX自動投稿（@wansakansai）

- 危険情報に変更があった場合、追加・更新エントリを自動でXにポスト（削除はポストしない）
- タスク内の STEP 6.5 で実行。`scripts/post_danger_to_x.py` が差分検出 + Cookieリフレッシュ + 投稿を担当
- 差分検出は `scripts/dangers_prev.json`（前回スナップショット、.gitignore）と現在の dangers.json を比較
- 投稿ライブラリ: `C:/Users/imao_/.claude/x_poster.py`（汎用、Playwright使用）
- 投稿本文は「入口」位置づけで最低限（場所・種別）+ サイト誘導URL + ハッシュタグ5個（#わんさかんさい #犬のいる暮らし #{県}わんこ #犬の安全 #毒餌注意）
- 都道府県タグはlocationから自動判定（大阪/兵庫/京都/奈良/滋賀/和歌山、該当なしは「関西」）
- 文字数カウントはX内部仕様（日本語1文字=2、URL=23固定）で計算。280ウェイト上限（=日本語実質140文字）
- 投稿は `[data-testid="tweetButtonInline"]` が画面外になりがちなので **Ctrl+Enterショートカット** で送信
- 複数件の場合は1件ずつ分割投稿（間隔2秒）
- 投稿失敗してもタスクは続行（メール本文に失敗内容+投稿本文を記載、ユーザーが手動フォロー）
- 投稿結果は `scripts/x_post_result.json` に保存され、メール通知で本文確認可能

## X自動投稿 拡張（スポット・ブログ・週次・季節）

危険情報以外にもX自動投稿の導線を追加している。共通ヘルパーは `scripts/x_auto_helpers.py`（季節ウィンドウ判定、気象庁API天気取得、投稿履歴管理、文面バリエーション生成）。投稿履歴は `scripts/x_post_history.json`（.gitignore、重複回避用）。

**全機能共通の原則:**
- **嘘を流さない**: 桜/紅葉/水遊びは季節ウィンドウ内のみ季節フレーズ挿入（SEASONAL_WINDOWSで保守的に定義）。天気は気象庁APIで確認済みのみ言及。施設情報はspots.jsonの事実のみ使用
- **Bot感をなくす**: 各スクリプトでランダム遅延、文面テンプレートを複数用意してランダム選択、絵文字は最小限

**各機能:**

1. **今日のおすすめ** - `scripts/post_daily_spot.py`
   - スケジュール: 毎日19:00 JST（スクリプト内で0〜60分遅延 → 実投稿19:00〜20:10）
   - タスクID: `wansakansai-daily-spot`
   - 選出ロジック: 30日以内投稿済みスポット除外、60〜90日ペナルティ、シーズン中タグ+3.0、visited +0.5、重み付きランダム
   - オフシーズンの季節タグのみ持つスポットは除外、`stay-only`タグスポットも除外

2. **新規スポット追加時** - `scripts/post_new_spot.py <spot_id>`
   - スポット追加作業の最後に手動/自動で呼び出す
   - 「【新スポット追加】」プレフィックスで既存の daily post と見分ける
   - 投稿前遅延は短め（5〜20分）

3. **新規ブログ記事公開時** - `scripts/post_new_blog.py <slug>`
   - ブログ記事追加作業の最後に手動/自動で呼び出す
   - `blog/<slug>.html` のメタ情報（og:title, description）を自動抽出
   - 「【ブログ更新】」プレフィックス

4. **週次まとめ** - `scripts/post_weekly_digest.py`
   - スケジュール: 毎週日曜20:00 JST
   - タスクID: `wansakansai-weekly-digest`
   - `git log --diff-filter=A --since="7 days ago"` で新規追加ファイルを検出（`blog/*.html`のうちindex.html・drafts以外）
   - 90日以上投稿されていないスポットからピックアップ

5. **季節特集** - `scripts/post_seasonal_feature.py <tag>` （手動トリガー）
   - 季節の変わり目（桜開花、紅葉スタート、梅雨入りなど）に手動で実行
   - 対応タグ: `sakura`, `koyo`, `water`, `rain`
   - 該当タグのスポットを最大5件まとめて1投稿
   - オフシーズン実行は `--force` で明示する必要あり（安全装置）

**メール通知:**
- `send_notify.py wansakansai-daily` サブコマンドで daily/weekly/seasonal 全共通（投稿結果JSON `scripts/x_post_result.json` を渡す）
- 危険情報は従来通り `wansakansai` サブコマンド

## X認証（Cookie自動リフレッシュ）

- 専用プロファイルのChromeを **タスク実行時だけ headless で一時起動** し、CDP経由でCookieを借りる方式
- 通常時はChromeは動いていない（普段のブラウザ利用を邪魔しない）
- 専用プロファイル: `C:/Users/imao_/.claude/x_chrome_profile`（普段のChromeと完全分離）
- Chrome起動フラグ: `--remote-debugging-port=9222 --remote-allow-origins=* --user-data-dir=C:\Users\imao_\.claude\x_chrome_profile --headless=new`
  - Chrome 136+ のセキュリティ強化で、デフォルトプロファイルではdebug portが無効化されるため専用プロファイル必須
- リフレッシュスクリプト: `C:/Users/imao_/.claude/refresh_x_cookies.py`
  - `--auto` オプションでChromeの起動・終了も自動管理（headless）
  - Chrome起動 → `http://localhost:9222` にCDP接続 → x.comのCookie取得 → `secrets/x_storage_wansakansai.json` に上書き → Chrome終了
  - 失敗しても非エラー終了（既存Cookieで続行）
- 運用: 毎日21時のタスク実行時、headlessで起動→Cookie更新→終了。ユーザーには見えない
- ログイン状態はプロファイル（`x_chrome_profile`）に永続保存されるので、タスクのたびに起動しても再ログイン不要
- トラブル時:
  - Cookie失効（パスワード変更等） → 専用Chromeを手動起動して再ログインする必要あり:
    - 手動起動: `"C:\Program Files\Google\Chrome\Application\chrome.exe" --user-data-dir="C:\Users\imao_\.claude\x_chrome_profile"` （debug portなしでもログイン操作は可能）
    - @wansakansaiにログイン → Chrome閉じる → 次回タスクから自動反映
  - CDP接続失敗 → 既存Cookieで投稿試行 → 失敗時はメールに投稿本文が記載されるので手動フォロー
- 初期セットアップの残骸: `scripts/x_cookies_raw.json`（Cookie-Editor出力、gitignore）は初回のCookie取得のみに使用。現在は未使用

## プロファイルのキャッシュ自動クリア

- 専用Chromeプロファイルのキャッシュが運用で肥大化するため、投稿後に自動削除
- スクリプト: `C:/Users/imao_/.claude/clear_x_cache.py`
- `post_danger_to_x.py` の投稿成功後に `clear_account("wansakansai")` を呼び出す
- 削除対象: `Default/{Cache, Code Cache, GPUCache, DawnCache, DawnGraphiteCache, DawnWebGPUCache, Service Worker/CacheStorage, Service Worker/ScriptCache}`
- Cookie・ログイン情報・履歴・ブックマーク等は**削除しない**（ログイン維持）
- Chromeが動作中なら自動スキップ（プロファイルロック回避）
- 手動実行も可能: `python clear_x_cache.py wansakansai` / `python clear_x_cache.py all`（全アカウント）

## マルチアカウント対応（2アカウント以上でX自動投稿する場合）

- `refresh_x_cookies.py` の `PORTS` 辞書でアカウント別ポート番号を管理
- 現在: `wansakansai=9222`, `uchidokoro=9223`
- 新規アカウント追加時は `PORTS` 辞書に追記。ポート番号はアカウント別に必ず分ける（同時実行時の競合回避）
- プロファイルは `x_chrome_profile_{account}` 形式で分離

# 犬阪んさい（wansakansai.com）

## プロジェクト概要
関西エリアの犬連れお出かけスポットを現在地から近い順に探せる静的Webサイト。

- **読み**: わんさかんさい
- **ホスティング**: GitHub Pages（wansakansai.com）
- **ターゲット**: 関西在住・関西旅行中の犬の飼い主

## 技術構成
- HTML + CSS + Vanilla JS（フレームワーク不使用）
- スポットデータ: JSON管理（data/spots.json）
- 地図: Google Maps iframe埋め込み（APIキー不要）
- お問い合わせ: Googleフォーム埋め込み
- AdSense審査対応（ads.txt設置、プライバシーポリシー完備）
- ナビゲーション: common.jsのSITE_NAV定数で一元管理（ページ追加時は1行追加するだけ）
- 都道府県フィルター: spots.jsonの住所から自動抽出（ハードコードなし）
- 個別対応は避け、テンプレート化・データ駆動を基本方針とする

## ページ構成
1. **トップページ** - GPS検索・フィルター・スポット一覧
2. **スポット詳細** - 各スポット情報・地図・SNSシェアボタン・関連危険情報
3. **危険情報** - 毒餌・事故情報（日付付き、毎日自動更新）
4. **このサイトについて** - 運営者情報・愛犬こつぶの紹介
5. **プライバシーポリシー**
6. **お問い合わせ** - Googleフォーム埋め込み済み
7. **404ページ** - チワワイラスト付き

## SEO・収益化
- Google Analytics設置済み（G-NPGCWSCZGB）
- Google Search Console登録済み（metaタグ認証 + HTMLファイル認証）
  - 旧プロパティ: https://imotan-lab.github.io/wansakansai/
  - 新プロパティ: http://wansakansai.com/（2026-04-06追加、HTMLファイル認証）
  - HTTPS版: https://wansakansai.com/（2026-04-08追加）
- sitemap.xml / robots.txt 設置済み
- sitemap.xmlのベースURLはwansakansai.com（generate_sitemap.pyのBASE_URL）
- OGPタグ設置済み（画像: images/ogp.png）-- 各ページに静的HTML版+JSでの動的更新
- canonical URL: 全ページに設定済み（spot.htmlはJSで動的更新）
- JSON-LD構造化データ: index.htmlにWebSite、spot.jsでPlace（スポットごとに動的生成）
- 画像最適化済み（ロゴ・スタンプ等をリサイズ、合計8.3MB→435KBに削減）
- AdSense申請済み（pub-2097489177716087、2026-04-09申請、審査待ち）
- ads.txt設置済み（pub-2097489177716087）
- AdSenseコード: 全HTMLページのheadに設置済み
- 広告枠（ad-slot）はdisplay:noneで非表示中、AdSense審査通過後に有効化する
- 独自ドメイン: wansakansai.com（お名前.comで取得済み、Aレコード+AAAAレコード設定済み）

## スポットデータ項目
名前、住所、GPS座標、駐車場、トイレ（洋式/和式）、ドッグラン（エリア分離有無・詳細）、入場料、`visited`フラグ（実訪問済みマーク）、`aliases`（別名リスト、検索・危険情報照合に使用。ひらがな読み・略称・通称を含む）、`tags`（汎用タグ配列: sakura, koyoなど）、備考、公式URL

## スポット名検索
- トップページの危険情報バナー下に検索入力欄を配置
- name, aliases, addressを対象に部分一致検索
- カタカナ⇔ひらがな自動変換、記号（中黒・ハイフン・スペース）無視
- 既存フィルター（都道府県・タグ）と組み合わせ可能
- デバウンス200msでリアルタイム検索
- 全129スポットにひらがな読みをaliasesに登録済み（pykakasiで生成、手動修正済み）

## フィルター機能
- 都道府県・条件タグの2段構成、いずれもトグル式（複数選択可、AND条件）
- フィルター定義はapp.jsのFILTER_GROUPS配列でカテゴリごとにグループ管理
- グループ: 駐車場（無料/有料/なし）、施設（ドッグラン/トイレ）、料金（入場無料/有料）、特徴（桜/紅葉/水遊び/小型犬のみ/雨でもOK）
- タグ系フィルター（桜・紅葉等）はspots.jsonのtagsフィールドを参照
- 新しいタグを追加する手順: spots.jsonのtagsに値を追加 → FILTER_GROUPSに1行追加
- GPS取得後もフィルターは維持される（フィルター→距離ソートの順で処理）

## デザイン
- モバイルファースト・レスポンシブ
- 温かみのあるアースカラー配色
- フォント: Noto Sans JP

## 許可されている操作
- Bashコマンドの実行（git, gh, python, npm等すべて）
- ファイルの読み書き・編集
- Gitの操作（commit, push, pull等）
- GitHub CLIの操作（リポジトリ作成、Pages設定等）
- ローカルサーバーの起動・停止
- Webブラウザ操作（プレビュー確認）
- Chrome（MCP）でのサイト確認は自由に行ってOK。使い終わったらタブを閉じること

## 公開URL
- 独自ドメイン: https://wansakansai.com（メイン）
- GitHub Pages: https://imotan-lab.github.io/wansakansai/（独自ドメインにリダイレクト）

## 作業フロー
- コード変更後は必ず git commit → git push する
- **スポットを追加・削除したら** `python generate_sitemap.py` を実行してsitemap.xmlを再生成してからコミットすること
- プッシュ後はデプロイ完了を待ち、本番サイト https://wansakansai.com を確認する
- 本番確認はプレビューツールのヘッドレスブラウザで行う（Chromeに干渉しない）
  - preview_startでローカルサーバー起動 → preview_evalで本番URLにナビゲート → preview_screenshotで確認
- 確認結果を報告し、ユーザーにも確認してもらう
- 絵文字は使わない（AI特有の表現を避ける）

## コンテンツ方針
- スポット追加は無料で行ける場所（入場無料・駐車場無料）をメインに集める
- 有料スポットも掲載OKだが、無料スポットを優先
- **宿泊オンリー施設は原則掲載しない**（日帰り利用可能な施設のみOK）。ただし運営者が実際に訪問・宿泊した場所は例外的に掲載OK
- 大阪府のスポットをメインに充実させる（他府県も掲載OKだがサブ）
- スポット画像は自分で撮影したものを使用（ネット上の画像は著作権NG）
- 写真は横向き（16:9）メインで撮影推奨（縦でも使える）
- 写真をまとめて渡してもらい、Claudeが良いものを選んでサイトに反映する
- 写真に人が写っている場合はPythonで顔検出＆ぼかし処理を行う
- 顔ぼかしスクリプト: blur_faces.py（YuNet DNN使用、モデルファイルは C:/Users/oh_so/face_detection_yunet.onnx）
- **顔ぼかしの標準手順（近つ飛鳥で確立した方法。毎回この手順で処理すること）**:
  1. `detect_faces_yunet(img, score_threshold=0.3)` でYuNet検出を実行し、検出結果の座標とスコアを全件出力
  2. 検出結果が実際の人物か、誤検出（木の枝・犬の顔・看板文字・模様など）かを**目視で判別**
  3. 誤検出が含まれる場合は**y座標（または領域）でフィルタ**して除外（例: `if y >= min_y` で上半分の誤検出を除外）
  4. フィルタ後の検出結果だけを `blur_face_ellipse()` でぼかす（楕円形、背景への影響最小）
  5. 処理結果を拡大してユーザーに確認してもらう → 問題があれば座標フィルタを調整して再処理
- **やってはいけないこと**: 検出結果をそのままぼかして「たぶん大丈夫」で済ませる。必ず検出座標を出力してから目視判別する。遠くの小さい人物には score_threshold を下げる。食べ物・看板・犬のみの写真は誤検出が多いので、人がいないと判断できる写真は検出自体をスキップする。

## スポット情報 定期チェック（自動タスク）
- 毎日 PM10:00 JST にローカルスケジュールタスクで実行
- タスクID: wansakansai-spot-check
- 10件ずつ順番にチェック、約2週間で全件1周
- 複数サイト突き合わせ + ブログ・SNS犬連れ実績確認
- 問題があればspots.jsonを修正してcommit & push
- ログ: C:\Users\imao_\.claude\logs\spot_check_YYYY-MM-DD.log（7日分保持）
- 進捗管理: C:\Users\imao_\Documents\wansakansai\spot_check_progress.json
- ログ出力はlog.py経由。log.pyはログ名で出力先を振り分け: spot_check_*とwansakansai_*は.claude/logs/へ、それ以外はDocuments/uchidokoro/logs/へ

## 危険情報（data/dangers.json）
- 毎日自動更新あり（毎日 PM9:00 JST、ローカルスケジュールタスクで実行）
- タスクID: wansakansai-danger-update
- 実行後にメール通知（send_notify.py wansakansai）
- ログ: C:\Users\imao_\.claude\logs\wansakansai_YYYY-MM-DD.log（7日分保持）
- Dropboxバックアップ: C:\Users\imao_\今電 Dropbox\今電　今尾笙夢\Claude_backup\自動タスク\wansakansai-danger-update\
- 旧リモートトリガー（trig_01P99nejNKkymiirUC8BpUJn）は一時停止済み
- 情報源: 自治体公式サイト + SNS（X、Instagram、Threads）
- SNS情報は「SNS上の報告」等と明記し、公式情報と区別する
- 1件だけの未確認情報は掲載しない（複数アカウントからの報告があるもののみ）
- ただし危険情報（毒餌・事故等の注意喚起）はSNS情報であることを明記すれば1件でも掲載OK（注意喚起は誤情報でも気をつけるに越したことはないため）
- 3ヶ月以上前で続報なし・解決済みの情報は削除を検討

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

## X認証（Cookie自動リフレッシュ）
- 専用プロファイルのChromeを常駐起動し、CDP（Chrome DevTools Protocol）経由でCookieを借りる方式
- 専用プロファイル: `C:/Users/imao_/.claude/x_chrome_profile`（普段のChromeと完全分離）
- Chrome起動フラグ: `--remote-debugging-port=9222 --remote-allow-origins=* --user-data-dir=C:\Users\imao_\.claude\x_chrome_profile`
  - Chrome 136+ のセキュリティ強化で、デフォルトプロファイルではdebug portが無効化されるため専用プロファイル必須
- 自動起動: スタートアップフォルダに `Chrome-Debug.lnk`（PC起動時に自動立ち上げ）
  - パス: `C:\Users\imao_\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup\Chrome-Debug.lnk`
- リフレッシュスクリプト: `C:/Users/imao_/.claude/refresh_x_cookies.py`
  - `http://localhost:9222` にCDP接続してx.comのCookie取得 → `secrets/x_storage_wansakansai.json` に上書き
  - 失敗しても非エラー終了（既存Cookieで続行）
- 運用: 会社PC 24h稼働 + 専用Chrome常駐でCookie実質無期限（X側のセッションリフレッシュを借りる）
- トラブル時:
  - 専用Chromeを誤って閉じた → スタートアップのショートカットで再起動。ログイン状態は保持される
  - Cookie失効（パスワード変更等） → 専用Chromeで再ログイン → 次回の自動リフレッシュで反映
  - CDP接続失敗 → 既存Cookieで投稿試行 → 失敗時はメールに投稿本文が記載されるので手動フォロー
- 初期セットアップの残骸: `scripts/x_cookies_raw.json`（Cookie-Editor出力、gitignore）は初回のCookie取得のみに使用。現在は未使用

## 危険情報とスポットの連動
- スポット詳細ページ（spot.html）: スポット名がdangers.jsonに含まれていれば危険情報を警告表示
- 危険情報ページ（danger.html）: スポット名がdangers.jsonに含まれていればスポット詳細へのリンクを表示
- JSによる動的照合のため、JSONデータの更新だけでリンクが自動追従する
- 照合はスポット名 + aliases（別名）で行う。個別ロジックではなくaliasesで対応する方針
- スポット追加時、正式名称以外で呼ばれそうな名前があればaliasesに入れる（例: 道の駅のプレフィックスなし、括弧内の名前、通称など）

## スポット情報の調査ルール
**スポット追加・更新時は必ずこのルールを守ること。1サイト調査で書くと誤情報が大量混入する（87件中18件の誤りが発覚した実績あり）。**

- 施設情報（ドッグランのルール・体重/体高制限・入場料・駐車場・営業時間など）は**必ず複数サイト（公式サイト＋2サイト以上）で突き合わせてから**spots.jsonに書くこと
- 調査エージェントへの指示に「**複数サイトを突き合わせて不一致を報告せよ**」と明示的に含めること
- 特に以下は複数サイト確認必須:
  - ドッグランのエリア分離・体重/体高制限
  - 駐車場の無料/有料・**具体的な台数**（季節によって変わる場合も注意）
  - 入場料・利用料金（値上がりしやすい、**必ず税込表記で公式の最新ページから取得**）
  - **犬のサイズ制限・犬種制限**（大型犬NG、小型犬のみ等。ドッグランと店内で条件が違うケースあり）
  - **住所の番地まで正確に**（公式サイトと地図サイトで一致確認）
  - **営業時間・定休日**（夏季/冬季で変わる場合も。ナイト営業があるか）
  - **2025〜2026年の値上げ情報**に特に注意
  - **マナーパンツ/ベルト着用必須か、ワクチン接種証明書の提示が必要か**
- 調査エージェントへの指示には上記チェック項目を**具体的に列挙**して伝えること（抽象的な指示だと見落とす）
- **複数サイト + SNS（X、Instagram、食べログ、わんわんスタジアム等）でも必ず突き合わせる**こと。公式だけだと最新の運用実態が反映されていない場合がある（マナーパンツ必須化、料金改定、犬種制限変更など）。SNSや個人ブログで見つかった最新情報も参照して整合性を取る
- 1サイトのみの情報で断定的に書かない。不確かな情報は「要確認」「推奨」など表現を和らげる
- **個人ブログ・SNS（X、Instagram等）でも犬連れ訪問の実績を確認すること**。公式サイトに犬OKと書いてなくても、実際に犬連れで行っている人がいれば掲載OK。逆に犬NGの情報があれば掲載しない
- 調査エージェントへの指示に「**ブログ・SNSでの犬連れ訪問実績も確認せよ**」と明示的に含めること
- ユーザーの実体験と食い違う場合はユーザー側を優先し、ネット情報を修正・削除する

## スポット追加時のチェックリスト
スポットを追加・更新するたびに以下を確認すること。

- [ ] 複数サイトで情報を突き合わせたか（公式＋2サイト以上）
- [ ] 個人ブログ・SNSで犬連れ訪問の実績があるか（犬NG情報がないか）
- [ ] `tags`の付け忘れがないか
  - `sakura`: 桜の名所として知られているか
  - `koyo`: 紅葉の名所として知られているか
  - `water`: 川遊び・水遊びができるか
  - `small-dog-only`: 小型犬のみ入場可（大型犬不可・要確認の場合）
  - `rain`: 雨でもOK（屋内施設・屋根付きエリアがある）
  - 今後タグが増えたら本リストも更新する
- [ ] `aliases`に通称・略称・別名が漏れていないか
- [ ] `visited`フラグが正しいか（実訪問済みならtrue）
- [ ] `officialUrl`が正しいか（公式サイトまたは公式観光情報サイト）

## スポット写真
- spots.jsonの`images`フィールドに複数画像パスを配列で指定（`imageUrl`は1枚目と同じ値）
- 画像は `images/spots/{スポットID}/` に配置
- スポット詳細ページにギャラリー表示あり（矢印ナビ + サムネイル切替）
- Web用リサイズ: 幅1200px、JPEG品質82〜85

## ブログ
- 記事一覧: `blog/index.html`（公開済み、ナビから遷移可能）
- 記事ページ: `blog/` ディレクトリに個別HTMLで配置
- ブログ用画像: `images/blog/{記事スラッグ}/` に配置
- 下書き: `blog/drafts/` にMarkdownで保存
- 現在2記事公開済み（近つ飛鳥の桜、滋賀・琵琶湖1泊2日旅）
- ナビゲーション: SITE_NAVに「ブログ」追加済み（危険情報の後に配置）
- 記事追加手順: HTMLを `blog/` に配置 → `blog/index.html` にカードを追加

## ドメイン移行時のTODO
独自ドメイン（wansakansai.com）の移行作業。HTTPS有効化済み（2026-04-08完了）。
- [x] DNS Aレコード設定（GitHub Pages IP x4）
- [x] DNS AAAAレコード設定（GitHub Pages IPv6 x4）
- [x] Search Consoleに http://wansakansai.com を新しいプロパティとして追加（HTMLファイル認証）
- [x] sitemap.xmlのURLをwansakansai.comに更新・送信（133件）
- [x] 旧URL（imotan-lab.github.io/wansakansai）からのリダイレクト動作確認（301）
- [x] SSL証明書発行・HTTPS強制有効化（2026-04-08完了）
- [x] HTTPSでの表示崩れ確認（2026-04-08確認済み、問題なし）
- [x] Search Consoleに https://wansakansai.com/ プロパティ追加・sitemap送信（2026-04-08完了）

## 注意事項
- uchidokoroフォルダ・ファイルには絶対に触れないこと
- セッション中に汎用的な運用ルールや仕組みが決まったら、ユーザーに言われなくてもCLAUDE.mdとメモリの両方に自動で保存すること

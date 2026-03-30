import json

with open('data/spots.json', 'r', encoding='utf-8') as f:
    spots = json.load(f)

def get(sid):
    return next(s for s in spots if s['id'] == sid)

fixes = []

# 1. むろいけ園地: 住所修正
s = get('muroike-enchi')
s['address'] = '大阪府四條畷市大字逢阪458-2'
fixes.append('むろいけ園地: 住所 459-2 → 458-2')

# 2. 浜寺公園: ドッグラン体高基準追加
s = get('hamadera-park')
s['dogRun']['detail'] = '小型犬エリア（体高50cm以下）・中大型犬エリアの2区画'
fixes.append('浜寺公園: ドッグラン体高50cm以下の基準追加')

# 3. 東部公園: 小型犬体重表記修正
s = get('hirakata-tobu-park')
s['dogRun']['detail'] = '小型犬エリア（体高40cm未満・体重概ね10kg未満）・中大型犬エリアの2区画'
fixes.append('東部公園: 小型犬「10kg以下」→「概ね10kg未満」')

# 4. 蜻蛉池公園: 料金改定（2025年12月改定）
s = get('tonbo-ike-park')
s['dogRun']['detail'] = '小型犬専用エリア・中大型犬優先エリアの2区画（WAN-TO）。ビジター料金: 平日600円/頭、土日祝1,600円/頭。2025年12月改定。'
fixes.append('蜻蛉池公園: 料金改定 平日600円・土日1,600円')

# 5. りんくうアイスパーク: 体重7kg未満追加
s = get('rinku-ice-park-dogrun')
s['dogRun']['detail'] = '小型犬エリア（7kg未満）・大型犬エリアの2区画'
fixes.append('りんくうアイスパーク: 小型犬7kg未満の基準追加')

# 6. 住之江公園: separated修正・登録料追記
s = get('suminoe-park')
s['dogRun']['separated'] = False
s['dogRun']['detail'] = '1エリア・時間帯優先制（奇数日:小型犬優先/偶数日:中大型犬優先）。2024年10月より利用登録制・初回登録料1頭500円（利用料は無料）。'
fixes.append('住之江公園: separated false・登録料500円追記')

# 7. 鶴見緑地: ドッグランあり（有料）に変更
s = get('tsurumi-ryokuchi')
s['dogRun']['available'] = True
s['dogRun']['free'] = False
s['dogRun']['separated'] = True
s['dogRun']['detail'] = '大阪鶴見緑地パートナードッグタウン（有料・S/M/L 3エリア）。新規登録300円+利用料500円/頭・回。新規登録は土日祝のみ要予約。'
fixes.append('鶴見緑地: ドッグランなし→有料ドッグランあり（パートナードッグタウン）')

# 8. 水軒公園: separated修正・3エリアに更新
s = get('suiken-park')
s['dogRun']['separated'] = True
s['dogRun']['detail'] = '大型犬エリア・小型犬エリア・第3エリアの3区画。犬種サイズ別に分離。無料。'
fixes.append('水軒公園: separated true・3エリア分離に更新')

# 9. 片男波公園: 駐車場有料に修正
s = get('kataonanami-park')
s['parking']['free'] = False
s['remarks'] = '万葉集にも詠まれた和歌の浦に面した海浜公園。砂浜・松林・野鳥の池など自然が豊か。犬連れ散歩可。駐車場有料（1時間100円、当日最大400円。7・8月は1,000円/日）。'
fixes.append('片男波公園: 駐車場 無料→有料')

# 10. 大池遊園: 桜シーズン駐車場有料の注記追加
s = get('oike-yuen')
s['remarks'] = '池の周囲に約700本の桜が咲く和歌山県屈指の花見スポット。ボート乗り場・遊具あり。犬連れ散策可。駐車場通常無料（桜まつり期間3月下旬〜4月上旬は有料）。'
fixes.append('大池遊園: 桜シーズン駐車場有料の注記追加')

# 11. 護摩壇山森林公園: 住所修正
s = get('gomadanzan-forest-park')
s['address'] = '和歌山県田辺市龍神村龍神918-61'
fixes.append('護摩壇山森林公園: 住所 龍神1020 → 龍神918-61')

# 12. 黒潮公園: sakuraタグ追加
s = get('kuroshio-park')
if 'sakura' not in s.get('tags', []):
    s.setdefault('tags', []).append('sakura')
fixes.append('黒潮公園: sakuraタグ追加')

# 13. びわ湖バレイ: 入場料修正
s = get('biwako-valley')
s['admission']['fee'] = 'ロープウェイ往復 大人4,000円、犬1頭500円（ケージ利用）'
fixes.append('びわ湖バレイ: 大人 3,500円 → 4,000円')

# 14. びわこ箱館山: 入場料修正
s = get('biwako-hakodateyama')
s['admission']['fee'] = '大人2,600円、こども1,300円、ペット700円（ゴンドラ往復込み）'
fixes.append('びわこ箱館山: 大人2,600円・こども1,300円に修正')

# 15. ブルーメの丘: 犬500円追加
s = get('blumenooka')
s['admission']['fee'] = '大人1,500円、小人800円、犬500円'
fixes.append('ブルーメの丘: 犬入園料500円追加')

# 16. 神戸フルーツ・フラワーパーク: separated修正・detail更新
s = get('kobe-fruit-flower-park')
s['dogRun']['separated'] = True
s['dogRun']['detail'] = '小型犬優先エリアとフリーエリア（中大型犬可）の2区画。フェンスで分離。'
fixes.append('神戸フルーツ・フラワーパーク: separated false→true')

# 17. 中之島公園: sakuraタグ追加
s = get('nakanoshima-park')
if 'sakura' not in s.get('tags', []):
    s.setdefault('tags', []).append('sakura')
fixes.append('中之島公園: sakuraタグ追加')

# 18. 箕面公園: sakuraタグ追加
s = get('minoo-park')
if 'sakura' not in s.get('tags', []):
    s.setdefault('tags', []).append('sakura')
fixes.append('箕面公園: sakuraタグ追加')

with open('data/spots.json', 'w', encoding='utf-8') as f:
    json.dump(spots, f, ensure_ascii=False, indent=2)

print(f'修正完了: {len(fixes)}件')
for f in fixes:
    print(f'  - {f}')

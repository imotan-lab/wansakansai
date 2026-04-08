import json

with open('data/spots.json', 'r', encoding='utf-8') as f:
    spots = json.load(f)

existing_ids = {s['id'] for s in spots}

new_spots = [
    {
        "id": "hitokura-park",
        "name": "兵庫県立一庫公園",
        "address": "兵庫県川西市国崎字知明1-6",
        "lat": 34.9078,
        "lng": 135.3933,
        "parking": {"available": True, "free": True},
        "toilet": {"available": True, "western": True},
        "dogRun": {"available": False, "free": False, "separated": False, "detail": ""},
        "admission": {"free": True, "fee": ""},
        "visited": False,
        "tags": ["koyo"],
        "aliases": ["一庫公園"],
        "remarks": "一庫ダム湖畔に広がる水辺・丘・山の3ゾーンで構成される自然公園。リード着用で散策可能。丘の駐車場（74台）と湖畔の駐車場（76台）の2箇所あり。秋の紅葉が美しい。",
        "officialUrl": "https://hitokura-park.com/"
    },
    {
        "id": "denspo-dogrun",
        "name": "北神戸田園スポーツ公園（でんスポ）",
        "address": "兵庫県神戸市北区有野町二郎753-1",
        "lat": 34.8465,
        "lng": 135.2227,
        "parking": {"available": True, "free": False},
        "toilet": {"available": True, "western": True},
        "dogRun": {"available": True, "free": False, "separated": False, "detail": "天然芝540平米。年間登録料500円/頭。狂犬病予防注射済証・3種以上ワクチン接種証明書が必要。事前登録必須。"},
        "admission": {"free": True, "fee": ""},
        "visited": False,
        "tags": [],
        "aliases": ["でんスポ", "北神戸田園スポーツ公園"],
        "remarks": "神戸市営のスポーツ公園内にある天然芝ドッグラン。駐車場は平日2時間無料・以降有料、土日祝は1時間200円〜（上限500円）。ドッグラン利用には事務所での事前登録が必要（受付9時-17時）。",
        "officialUrl": "https://www.denspo.com/facility/dogrun/"
    },
    {
        "id": "awaji-hanasajiki",
        "name": "あわじ花さじき",
        "address": "兵庫県淡路市楠本2805-7",
        "lat": 34.5994,
        "lng": 135.0003,
        "parking": {"available": True, "free": False},
        "toilet": {"available": True, "western": True},
        "dogRun": {"available": False, "free": False, "separated": False, "detail": ""},
        "admission": {"free": True, "fee": ""},
        "visited": False,
        "tags": [],
        "aliases": ["花さじき"],
        "remarks": "明石海峡・大阪湾を背景に四季の花畑が広がる県立公園。入場無料、駐車場200円/回。リード短く保持で犬同伴OK。花さじきテラス館内はペット不可。春は菜の花、秋はコスモスが見頃。",
        "officialUrl": "https://awajihanasajiki.jp/"
    },
    {
        "id": "awajishima-park",
        "name": "兵庫県立淡路島公園",
        "address": "兵庫県淡路市楠本2425-2",
        "lat": 34.5893,
        "lng": 135.0167,
        "parking": {"available": True, "free": True},
        "toilet": {"available": True, "western": True},
        "dogRun": {"available": False, "free": False, "separated": False, "detail": ""},
        "admission": {"free": True, "fee": ""},
        "visited": False,
        "tags": ["sakura"],
        "aliases": ["淡路島公園"],
        "remarks": "約150haの広大な県立公園。無料駐車場9箇所（計337台）。リード着用で犬同伴可。アトラクションや屋内施設はペット不可。芝生広場が広く犬の散歩に最適。淡路SAから直結。春は桜の名所。",
        "officialUrl": "https://www.hyogo-park.or.jp/awajishima/"
    },
    {
        "id": "ako-kaihin-park",
        "name": "兵庫県立赤穂海浜公園",
        "address": "兵庫県赤穂市御崎1857-5",
        "lat": 34.7319,
        "lng": 134.3697,
        "parking": {"available": True, "free": False},
        "toilet": {"available": True, "western": True},
        "dogRun": {"available": False, "free": False, "separated": False, "detail": ""},
        "admission": {"free": True, "fee": ""},
        "visited": False,
        "tags": [],
        "aliases": ["赤穂海浜公園"],
        "remarks": "瀬戸内海に面した塩田跡地の都市公園。入園無料、駐車場500円/回。無料エリアのみペット同伴可（リード必須）。広い芝生広場や遊歩道あり。火曜定休。",
        "officialUrl": "https://www.hyogo-park.or.jp/akokaihin/"
    },
    {
        "id": "ako-picnic-park",
        "name": "赤穂ピクニック公園",
        "address": "兵庫県赤穂市御崎314-4",
        "lat": 34.7279,
        "lng": 134.3774,
        "parking": {"available": True, "free": True},
        "toilet": {"available": True, "western": True},
        "dogRun": {"available": True, "free": True, "separated": True, "detail": "中大型犬用と小型犬用に分離。面積約625平米、フェンス高さ1.5m。犬専用水飲み場・リードフック完備。8:30-18:00（10-3月は-17:00）。"},
        "admission": {"free": True, "fee": ""},
        "visited": False,
        "tags": [],
        "aliases": ["ピクニック公園"],
        "remarks": "赤穂市運営の無料ドッグラン併設公園。駐車場50台無料。園内から瀬戸内海を一望できる。元牧場跡地を整備した緑豊かな公園。",
        "officialUrl": "https://www.city.ako.lg.jp/kensetsu/kouen/dogrun.html"
    },
    {
        "id": "michinoeki-chikusa",
        "name": "道の駅 ちくさ",
        "address": "兵庫県宍粟市千種町下河野745-5",
        "lat": 35.1349,
        "lng": 134.4600,
        "parking": {"available": True, "free": True},
        "toilet": {"available": True, "western": True},
        "dogRun": {"available": True, "free": False, "separated": True, "detail": "テニスコート10面分の広さ。小型犬優先エリア（人工芝）あり。ノーリードOK。利用料金は要確認。"},
        "admission": {"free": True, "fee": ""},
        "visited": False,
        "tags": ["water"],
        "aliases": ["ちくさ"],
        "remarks": "「わんこと楽しむ」がコンセプトの犬連れ特化型道の駅。ドッグラン・ドッグカフェ併設。デイキャンプ場では川遊びも可能。営業時間9:00-16:00。",
        "officialUrl": "https://mitinoekichikusa.wixsite.com/home"
    },
    {
        "id": "shirotopia-park",
        "name": "シロトピア記念公園",
        "address": "兵庫県姫路市本町68",
        "lat": 34.8415,
        "lng": 134.6932,
        "parking": {"available": True, "free": False},
        "toilet": {"available": True, "western": True},
        "dogRun": {"available": False, "free": False, "separated": False, "detail": ""},
        "admission": {"free": True, "fee": ""},
        "visited": False,
        "tags": ["sakura"],
        "aliases": ["シロトピア"],
        "remarks": "姫路城の北側に位置する芝生公園（約1.2ha）。犬連れ散歩OK。姫路城を望みながらの散策が楽しめる。城の北駐車場が隣接（最初30分無料・以降有料）。春は桜が美しい。",
        "officialUrl": "https://www.city.himeji.lg.jp/kanko/0000004650.html"
    },
    {
        "id": "maiko-park",
        "name": "県立舞子公園",
        "address": "兵庫県神戸市垂水区東舞子町2051",
        "lat": 34.6309,
        "lng": 135.0287,
        "parking": {"available": True, "free": False},
        "toilet": {"available": True, "western": True},
        "dogRun": {"available": False, "free": False, "separated": False, "detail": ""},
        "admission": {"free": True, "fee": ""},
        "visited": False,
        "tags": [],
        "aliases": ["舞子公園"],
        "remarks": "明石海峡大橋のたもとにある兵庫県最古の県立公園。リード着用で犬同伴OK。駐車場は1時間200円（上限1,000円）。明石海峡の大パノラマが楽しめる。JR舞子駅から徒歩5分。建物内はペット不可。",
        "officialUrl": "https://hyogo-maikopark.jp/"
    },
    {
        "id": "mikiyama-forest-park",
        "name": "兵庫県立三木山森林公園",
        "address": "兵庫県三木市福井字三木山2465-1",
        "lat": 34.7947,
        "lng": 134.9772,
        "parking": {"available": True, "free": True},
        "toilet": {"available": True, "western": True},
        "dogRun": {"available": False, "free": False, "separated": False, "detail": ""},
        "admission": {"free": True, "fee": ""},
        "visited": False,
        "tags": ["koyo"],
        "aliases": ["三木山森林公園"],
        "remarks": "甲子園球場約20倍（約80万平米）の広大な森林公園。入園・駐車場ともに無料。犬連れの利用者が多い。愛犬のお散歩マナー教室も定期開催。水曜定休。秋は紅葉が美しい。",
        "officialUrl": "https://mikiyama.net/"
    },
    {
        "id": "shiawasenomura",
        "name": "しあわせの村",
        "address": "兵庫県神戸市北区しあわせの村1-1",
        "lat": 34.7104,
        "lng": 135.1321,
        "parking": {"available": True, "free": False},
        "toilet": {"available": True, "western": True},
        "dogRun": {"available": False, "free": False, "separated": False, "detail": ""},
        "admission": {"free": True, "fee": ""},
        "visited": False,
        "tags": [],
        "aliases": [],
        "remarks": "花と緑あふれる総合福祉ゾーン。公園エリアのみリード着用でペット同伴可（キャンプ場・トリム園地・テニスコートはペット不可）。駐車場1日500円（条件付き無料あり）。三宮から車で約25分。",
        "officialUrl": "https://shiawasenomura.org/"
    },
    {
        "id": "amagasaki-mori-ryokuchi",
        "name": "兵庫県立尼崎の森中央緑地",
        "address": "兵庫県尼崎市扇町33-4",
        "lat": 34.7090,
        "lng": 135.4063,
        "parking": {"available": True, "free": True},
        "toilet": {"available": True, "western": True},
        "dogRun": {"available": False, "free": False, "separated": False, "detail": ""},
        "admission": {"free": True, "fee": ""},
        "visited": False,
        "tags": [],
        "aliases": ["尼崎の森中央緑地", "尼崎の森"],
        "remarks": "県立公園最大級の大芝生広場を持つ都市緑地。入園・駐車場（約1,000台）ともに無料。広大な芝生で犬の散歩に最適。9:00-17:00、年末年始休園。",
        "officialUrl": "https://www.hyogo-park.or.jp/amagasaki/"
    }
]

added = 0
for spot in new_spots:
    if spot['id'] not in existing_ids:
        spots.append(spot)
        existing_ids.add(spot['id'])
        added += 1
        print(f"  - {spot['name']}")
    else:
        print(f"  [skip] {spot['name']} (already exists)")

with open('data/spots.json', 'w', encoding='utf-8') as f:
    json.dump(spots, f, ensure_ascii=False, indent=2)

print(f"\n兵庫県{added}件追加 (合計{len(spots)}件)")

import json

with open('data/spots.json', 'r', encoding='utf-8') as f:
    spots = json.load(f)

existing_ids = {s['id'] for s in spots}

new_spots = [
    {
        "id": "kyoto-gyoen",
        "name": "京都御苑",
        "address": "京都府京都市上京区京都御苑3",
        "lat": 35.024757,
        "lng": 135.763946,
        "parking": {"available": True, "free": False},
        "toilet": {"available": True, "western": True},
        "dogRun": {"available": False, "free": False, "separated": False, "detail": ""},
        "admission": {"free": True, "fee": ""},
        "visited": False,
        "tags": ["sakura", "koyo"],
        "aliases": ["京都御所", "御所"],
        "remarks": "約65haの広大な国民公園。犬はリード必須（ロングリード不可）。京都御所内は宮内庁管轄のためペット不可。中立売休憩所のテラス席は犬OK。駐車場は中立売（131台）・清和院（81台）の2箇所、3時間800円。",
        "officialUrl": "https://fng.or.jp/kyoto/"
    },
    {
        "id": "tetsugaku-no-michi",
        "name": "哲学の道",
        "address": "京都府京都市左京区銀閣寺町付近〜若王子町付近",
        "lat": 35.0273,
        "lng": 135.796838,
        "parking": {"available": False, "free": False},
        "toilet": {"available": True, "western": True},
        "dogRun": {"available": False, "free": False, "separated": False, "detail": ""},
        "admission": {"free": True, "fee": ""},
        "visited": False,
        "tags": ["sakura", "koyo"],
        "aliases": [],
        "remarks": "琵琶湖疏水分線沿い約1.5kmの散歩道。車両進入禁止で犬の散歩に最適。銀閣寺〜南禅寺を結ぶ。専用駐車場なし（周辺コインパーキング利用）。",
        "officialUrl": "https://tetsugakunomichi.jp/"
    },
    {
        "id": "kamogawa-park",
        "name": "鴨川公園",
        "address": "京都府京都市北区出雲路松ノ下町",
        "lat": 35.041846,
        "lng": 135.763057,
        "parking": {"available": True, "free": False},
        "toilet": {"available": True, "western": True},
        "dogRun": {"available": False, "free": False, "separated": False, "detail": ""},
        "admission": {"free": True, "fee": ""},
        "visited": False,
        "tags": ["sakura", "water"],
        "aliases": ["鴨川河川敷", "鴨川デルタ", "出町柳"],
        "remarks": "鴨川の河川敷を整備した公園。出町柳の鴨川デルタ付近は浅瀬で犬の水遊びも可能。リード必須。下鴨神社・糺の森にも近い。周辺コインパーキング利用推奨。",
        "officialUrl": "https://www.pref.kyoto.jp/koen-annai/kamo.html"
    },
    {
        "id": "takaraike-park",
        "name": "宝が池公園",
        "address": "京都府京都市左京区上高野流田町8",
        "lat": 35.058011,
        "lng": 135.790273,
        "parking": {"available": True, "free": False},
        "toilet": {"available": True, "western": True},
        "dogRun": {"available": False, "free": False, "separated": False, "detail": ""},
        "admission": {"free": True, "fee": ""},
        "visited": False,
        "tags": ["sakura", "koyo"],
        "aliases": ["宝ヶ池公園", "宝ヶ池"],
        "remarks": "周囲約1.5kmの宝ヶ池を中心とした自然公園。犬はリード着用で園路を散歩可能（芝生広場・植樹帯は犬不可）。子どもの楽園エリアもペット不可。駐車場30分100円。",
        "officialUrl": "https://www.city.kyoto.lg.jp/kensetu/page/0000082746.html"
    },
    {
        "id": "byodoin",
        "name": "平等院",
        "address": "京都府宇治市宇治蓮華116",
        "lat": 34.890138,
        "lng": 135.807764,
        "parking": {"available": False, "free": False},
        "toilet": {"available": True, "western": True},
        "dogRun": {"available": False, "free": False, "separated": False, "detail": ""},
        "admission": {"free": False, "fee": "大人600円、中高生400円、小学生300円"},
        "visited": False,
        "tags": ["sakura", "koyo"],
        "aliases": ["平等院鳳凰堂", "宇治平等院"],
        "remarks": "世界遺産。庭園のみ犬連れ拝観可（リード必須）。鳳凰堂内部・ミュージアム鳳翔館はペット不可。専用駐車場なし（宇治駐車場700円等を利用）。",
        "officialUrl": "https://www.byodoin.or.jp/"
    },
    {
        "id": "keihanna-park",
        "name": "けいはんな記念公園",
        "address": "京都府相楽郡精華町精華台6-1",
        "lat": 34.746982,
        "lng": 135.776982,
        "parking": {"available": True, "free": False},
        "toilet": {"available": True, "western": True},
        "dogRun": {"available": False, "free": False, "separated": False, "detail": ""},
        "admission": {"free": True, "fee": ""},
        "visited": False,
        "tags": ["water"],
        "aliases": ["けいはんな公園"],
        "remarks": "無料区域（広場・谷あい）のみ犬同伴可。水景園（有料）とビジターセンターはペット不可。谷あいの小川で水遊び可能。駐車場400円。9:00-17:00。",
        "officialUrl": "https://keihanna-park.net/"
    },
    {
        "id": "kasagi-camp",
        "name": "笠置キャンプ場",
        "address": "京都府相楽郡笠置町笠置",
        "lat": 34.754031,
        "lng": 135.937255,
        "parking": {"available": True, "free": False},
        "toilet": {"available": True, "western": False},
        "dogRun": {"available": False, "free": False, "separated": False, "detail": ""},
        "admission": {"free": False, "fee": "日帰り：大人500円、小学生300円"},
        "visited": False,
        "tags": ["sakura", "water"],
        "aliases": ["笠置河原"],
        "remarks": "木津川沿いの河原キャンプ場。犬連れOK（リード短め）。予約不要・24時間入場可。車の場内乗り入れ可（約300台）。トイレは簡易水洗（トイレットペーパーなし）。桜の名所。",
        "officialUrl": "https://kankou-kasagi.com/kasagi-camp/"
    },
    {
        "id": "kameoka-sports-park",
        "name": "亀岡運動公園",
        "address": "京都府亀岡市曽我部町穴太土渕33-1",
        "lat": 35.006013,
        "lng": 135.534958,
        "parking": {"available": True, "free": True},
        "toilet": {"available": True, "western": True},
        "dogRun": {"available": False, "free": False, "separated": False, "detail": ""},
        "admission": {"free": True, "fee": ""},
        "visited": False,
        "tags": ["sakura"],
        "aliases": ["亀岡運動公園さくら公園"],
        "remarks": "広大な敷地にスポーツ施設・広場・ウォーキングロードを備えた公園。犬の散歩に人気（リード必須）。駐車場約705台無料。秋は隣接の夢コスモス園（別料金・犬OK・ドッグランあり）も楽しめる。",
        "officialUrl": "https://park-kameoka.jp/"
    },
    {
        "id": "michinoeki-kyotanba-ajimunosato",
        "name": "道の駅 京丹波 味夢の里",
        "address": "京都府船井郡京丹波町曽根深シノ65-1",
        "lat": 35.155995,
        "lng": 135.41615,
        "parking": {"available": True, "free": True},
        "toilet": {"available": True, "western": True},
        "dogRun": {"available": True, "free": True, "separated": False, "detail": "全犬種共用エリア。9:00-17:00。犬用シャワー・水飲み場・リードフック付きベンチあり。"},
        "admission": {"free": True, "fee": ""},
        "visited": False,
        "tags": [],
        "aliases": ["味夢の里", "京丹波PA"],
        "remarks": "京都縦貫道・京丹波PA併設の道の駅。無料ドッグランあり（エリア分離なし）。高速道路・一般道の両方からアクセス可。テラス席はペット同伴OK。",
        "officialUrl": "https://ajim.info/"
    },
    {
        "id": "miyama-kayabuki-no-sato",
        "name": "美山かやぶきの里",
        "address": "京都府南丹市美山町北",
        "lat": 35.316434,
        "lng": 135.617245,
        "parking": {"available": True, "free": False},
        "toilet": {"available": True, "western": True},
        "dogRun": {"available": False, "free": False, "separated": False, "detail": ""},
        "admission": {"free": True, "fee": ""},
        "visited": False,
        "tags": ["koyo"],
        "aliases": ["かやぶきの里", "美山"],
        "remarks": "国の重要伝統的建造物群保存地区。39棟の茅葺き屋根の集落を犬連れで散策可能（リード必須）。現役の住居地のため車両乗り入れ禁止。駐車場500円。秋の紅葉、冬の雪景色が見事。",
        "officialUrl": "https://kayabukinosato.jp/"
    },
    {
        "id": "fuminmori-hiyoshi",
        "name": "京都府立府民の森ひよし",
        "address": "京都府南丹市日吉町天若上ノ所25",
        "lat": 35.137478,
        "lng": 135.52969,
        "parking": {"available": True, "free": True},
        "toilet": {"available": True, "western": True},
        "dogRun": {"available": True, "free": False, "separated": True, "detail": "約7,000平米。小型犬エリア（10kg以下）・中大型犬エリア・フリーエリアの3区分。1頭510円（要確認、600円の情報もあり）。"},
        "admission": {"free": True, "fee": ""},
        "visited": False,
        "tags": [],
        "aliases": ["府民の森ひよし"],
        "remarks": "天若湖畔に広がる森林公園。約7,000平米の広大なドッグランは小型犬・中大型犬・フリーの3エリアに分離。キャンプ場・キャビンも併設。駐車場無料。",
        "officialUrl": "https://forest-hiyoshi.jp/"
    },
    {
        "id": "tango-oukoku-shoku-no-miyako",
        "name": "丹後王国「食のみやこ」",
        "address": "京都府京丹後市弥栄町鳥取123",
        "lat": 35.674305,
        "lng": 135.068474,
        "parking": {"available": True, "free": True},
        "toilet": {"available": True, "western": True},
        "dogRun": {"available": True, "free": False, "separated": True, "detail": "約2,300平米。小型犬専用エリアとフリーエリアの2区分。1頭500円（時間制限なし）。9:30-16:30。"},
        "admission": {"free": True, "fee": ""},
        "visited": False,
        "tags": [],
        "aliases": ["丹後王国", "道の駅丹後王国"],
        "remarks": "西日本最大級の道の駅。園内はペット同伴可（小動物園エリアは不可）。ドッグラン（約2,300平米）は小型犬エリアとフリーエリアに分離。テラス席で犬と食事可能。駐車場約520台無料。",
        "officialUrl": "https://tangooukoku.com/"
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

print(f"\n京都府{added}件追加 (合計{len(spots)}件)")

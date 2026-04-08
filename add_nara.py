import json

with open('data/spots.json', 'r', encoding='utf-8') as f:
    spots = json.load(f)

existing_ids = {s['id'] for s in spots}

new_spots = [
    {
        "id": "obuchi-ike-park",
        "name": "大渕池公園",
        "address": "奈良県奈良市中山町西1丁目839-1",
        "lat": 34.6894,
        "lng": 135.7636,
        "parking": {"available": True, "free": True},
        "toilet": {"available": True, "western": True},
        "dogRun": {"available": False, "free": False, "separated": False, "detail": ""},
        "admission": {"free": True, "fee": ""},
        "visited": False,
        "tags": ["sakura", "koyo"],
        "aliases": ["おおぶちいけこうえん"],
        "remarks": "大渕池を中心とした約23.5haの県立公園。東地区・西地区・池地区の3エリア。リード着用で犬の散歩可能。駐車場は東地区38台・西地区29台（いずれも無料）。",
        "officialUrl": "https://oobuchiike.osaka-park.or.jp/"
    },
    {
        "id": "crossway-nakamachi",
        "name": "道の駅クロスウェイなかまち",
        "address": "奈良県奈良市中町4694-1",
        "lat": 34.6686,
        "lng": 135.7617,
        "parking": {"available": True, "free": True},
        "toilet": {"available": True, "western": True},
        "dogRun": {
            "available": True,
            "free": True,
            "separated": True,
            "detail": "小型犬（10kg未満）・中大型犬（10kg以上）の2区画。登録制（狂犬病予防注射済票・混合ワクチン接種証明書・身分証明書を持参）。マナーウェア着用必須。9:00-17:00。"
        },
        "admission": {"free": True, "fee": ""},
        "visited": False,
        "tags": [],
        "aliases": ["クロスウェイなかまち"],
        "remarks": "2024年11月オープンの奈良県初の防災道の駅。駐車場237台（24時間利用可・無料）。直売所・レストラン等飲食施設充実。発情期の犬はドッグラン利用不可。",
        "officialUrl": "https://michi-no-eki-crosswaynakamachi.pref.nara.jp/"
    },
    {
        "id": "heijo-palace-park",
        "name": "平城宮跡歴史公園",
        "address": "奈良県奈良市二条大路南4-6-1",
        "lat": 34.6876,
        "lng": 135.7879,
        "parking": {"available": True, "free": False},
        "toilet": {"available": True, "western": True},
        "dogRun": {"available": False, "free": False, "separated": False, "detail": ""},
        "admission": {"free": True, "fee": ""},
        "visited": False,
        "tags": ["sakura"],
        "aliases": ["平城宮跡"],
        "remarks": "世界遺産「古都奈良の文化財」の構成資産。リード（2m以内）着用で犬の散策可能。復原建物周辺・建物内はペット不可。駐車場有料（1時間200円・当日上限500円）。約1,000本の桜の名所。",
        "officialUrl": "https://www.heijo-park.jp/"
    },
    {
        "id": "hari-terrace",
        "name": "道の駅針T・R・S",
        "address": "奈良県奈良市針町345",
        "lat": 34.5972,
        "lng": 136.0008,
        "parking": {"available": True, "free": True},
        "toilet": {"available": True, "western": True},
        "dogRun": {"available": False, "free": False, "separated": False, "detail": ""},
        "admission": {"free": True, "fee": ""},
        "visited": False,
        "tags": [],
        "aliases": ["針テラス", "針TRS", "道の駅針テラス"],
        "remarks": "名阪国道沿いの西日本最大級の道の駅。駐車場約500台（無料）。直売所・フードコート・レストラン等充実。犬連れでの施設外散策可。建物内はペット不可。",
        "officialUrl": "https://hari-trs.com/"
    },
    {
        "id": "ikoma-sanroku-park",
        "name": "生駒山麓公園",
        "address": "奈良県生駒市俵口町2088",
        "lat": 34.6831,
        "lng": 135.6889,
        "parking": {"available": True, "free": False},
        "toilet": {"available": True, "western": True},
        "dogRun": {"available": False, "free": False, "separated": False, "detail": ""},
        "admission": {"free": True, "fee": ""},
        "visited": False,
        "tags": ["sakura"],
        "aliases": [],
        "remarks": "生駒山中腹に広がる総合公園。リード着用で犬の散歩可能。フィールドアスレチック等の有料施設内はペット不可。駐車場有料（1回520円）。",
        "officialUrl": "https://ikoma36.jp/"
    },
    {
        "id": "yamato-minzoku-park",
        "name": "大和民俗公園",
        "address": "奈良県大和郡山市矢田町545",
        "lat": 34.6397,
        "lng": 135.7344,
        "parking": {"available": True, "free": True},
        "toilet": {"available": True, "western": True},
        "dogRun": {"available": False, "free": False, "separated": False, "detail": ""},
        "admission": {"free": True, "fee": ""},
        "visited": False,
        "tags": ["sakura"],
        "aliases": ["県立大和民俗公園"],
        "remarks": "約26.6haの敷地に古民家15棟を移築展示した公園。リード着用で犬の散歩可能。広い芝生エリアがあり自転車・ボール遊び禁止で犬連れでも安心。駐車場147台（無料）。梅林・しょうぶ園あり。",
        "officialUrl": "https://www.pref.nara.jp/7572.htm"
    },
    {
        "id": "yatayama-asobi-no-mori",
        "name": "矢田山遊びの森",
        "address": "奈良県大和郡山市矢田町2070",
        "lat": 34.6488,
        "lng": 135.7178,
        "parking": {"available": True, "free": True},
        "toilet": {"available": True, "western": True},
        "dogRun": {"available": False, "free": False, "separated": False, "detail": ""},
        "admission": {"free": True, "fee": ""},
        "visited": False,
        "tags": [],
        "aliases": ["県立矢田自然公園"],
        "remarks": "約300haの自然体験型公園。リード着用で犬の散歩可能。峠池を中心とした遊歩道やハイキングコースが整備。駐車場100台（無料・8:45-17:00）。車でのアクセスは細い山道あり注意。定休日は月曜。",
        "officialUrl": "https://www.pref.nara.jp/3053.htm"
    },
    {
        "id": "tenri-dam-fuchi-park",
        "name": "天理ダム風致公園",
        "address": "奈良県天理市長滝町",
        "lat": 34.5625,
        "lng": 135.8897,
        "parking": {"available": True, "free": True},
        "toilet": {"available": True, "western": False},
        "dogRun": {"available": False, "free": False, "separated": False, "detail": ""},
        "admission": {"free": True, "fee": ""},
        "visited": False,
        "tags": ["sakura", "koyo"],
        "aliases": ["天理ダム公園"],
        "remarks": "天理ダム周辺の山の斜面に整備された公園。犬連れでの散歩は可能と思われるが公式の明記なし（要確認）。駐車場約30台（無料）。ソメイヨシノ・ヤマザクラ約900本の桜の名所。バーベキュー施設あり。",
        "officialUrl": "https://www.city.tenri.nara.jp/kakuka/kensetsubu/toshiseibika/toshikouen/1390888992486.html"
    },
    {
        "id": "kashihara-sports-park",
        "name": "橿原運動公園",
        "address": "奈良県橿原市雲梯町323-2",
        "lat": 34.5178,
        "lng": 135.7756,
        "parking": {"available": True, "free": True},
        "toilet": {"available": True, "western": True},
        "dogRun": {"available": False, "free": False, "separated": False, "detail": ""},
        "admission": {"free": True, "fee": ""},
        "visited": False,
        "tags": [],
        "aliases": [],
        "remarks": "広大な敷地の総合運動公園。遊歩道でリード着用の犬の散歩が可能。駐車場718台（無料）。約120種・1,300株のバラ園が見どころ（春5月・秋10月）。スポーツ施設は有料。",
        "officialUrl": "https://kouen-kashi-sports.net/"
    },
    {
        "id": "asuka-historical-park",
        "name": "国営飛鳥歴史公園",
        "address": "奈良県高市郡明日香村大字平田538",
        "lat": 34.4647,
        "lng": 135.8106,
        "parking": {"available": True, "free": True},
        "toilet": {"available": True, "western": True},
        "dogRun": {"available": False, "free": False, "separated": False, "detail": ""},
        "admission": {"free": True, "fee": ""},
        "visited": False,
        "tags": ["sakura"],
        "aliases": ["飛鳥歴史公園"],
        "remarks": "高松塚・石舞台・甘樫丘・祝戸・キトラ古墳の5地区からなる国営公園（総面積約60ha）。リード（2m以内）着用で犬の散策可能。建物内はペット不可。公園内駐車場は無料。周辺の村営駐車場は有料の場合あり。",
        "officialUrl": "https://www.asuka-park.jp/"
    },
    {
        "id": "uda-animal-park",
        "name": "うだ・アニマルパーク",
        "address": "奈良県宇陀市大宇陀小附75-1",
        "lat": 34.4847,
        "lng": 135.9183,
        "parking": {"available": True, "free": True},
        "toilet": {"available": True, "western": True},
        "dogRun": {
            "available": True,
            "free": True,
            "separated": False,
            "detail": "登録制ドッグラン。利用には事前登録が必要。エリア分離の有無は要確認。"
        },
        "admission": {"free": True, "fee": ""},
        "visited": False,
        "tags": [],
        "aliases": ["うだアニマルパーク", "宇陀アニマルパーク"],
        "remarks": "奈良県営の動物ふれあい施設。入園料・駐車場ともに無料。園内の一部を除き犬の散歩可能（動物ふれあいエリア等は不可）。ドッグランは登録制。開園9:00-17:00。",
        "officialUrl": "https://www.pref.nara.jp/1839.htm"
    },
    {
        "id": "yoshimizu-shrine",
        "name": "吉水神社",
        "address": "奈良県吉野郡吉野町吉野山579",
        "lat": 34.3694,
        "lng": 135.8569,
        "parking": {"available": True, "free": True},
        "toilet": {"available": True, "western": True},
        "dogRun": {"available": False, "free": False, "separated": False, "detail": ""},
        "admission": {"free": True, "fee": ""},
        "visited": False,
        "tags": ["sakura", "koyo"],
        "aliases": [],
        "remarks": "世界遺産の神社でペット参拝OK。宮司が犬連れ大歓迎を公言。書院内も抱っこで拝観可能（書院拝観料：大人600円）。犬の健康長寿祈願・七五三のご祈祷も可能（要予約）。ペット用お守りあり。境内から「一目千本」の桜の絶景。専用駐車場は約5台と少ないため吉野山駐車場の利用推奨。",
        "officialUrl": "https://www.yoshimizu-shrine.com/"
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

print(f"\n{added}件追加 (合計{len(spots)}件)")

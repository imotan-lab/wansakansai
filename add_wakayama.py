import json

with open('data/spots.json', 'r', encoding='utf-8') as f:
    spots = json.load(f)

new_spots = [
    {
        "id": "shiki-no-sato-park",
        "name": "道の駅 四季の郷公園 FOOD HUNTER PARK",
        "address": "和歌山県和歌山市明王寺479-1",
        "lat": 34.2399,
        "lng": 135.1693,
        "category": "park",
        "dogSize": {"small": True, "large": True},
        "parking": {"available": True, "free": True},
        "toilet": {"available": True, "western": True},
        "stairs": 1,
        "barrierFree": 4,
        "dogRun": {"available": True, "free": True, "detail": "大型・中型犬と小型犬の2エリアに分離。無料。", "separated": True},
        "admission": {"free": True, "fee": ""},
        "visited": False,
        "remarks": "25.5haの広大な農業公園。関西トップクラスのドッグパークと評されるドッグランあり（大中型・小型分離、無料）。農産物直売所・レストランも充実。駐車場8ヶ所・無料。営業時間9:00〜17:00（火曜休）。",
        "imageUrl": "",
        "officialUrl": "https://fh-park.jp/",
        "aliases": ["四季の郷公園", "四季の郷"],
        "tags": []
    },
    {
        "id": "suiken-park",
        "name": "水軒公園",
        "address": "和歌山県和歌山市西浜1188",
        "lat": 34.2065,
        "lng": 135.1764,
        "category": "park",
        "dogSize": {"small": True, "large": True},
        "parking": {"available": True, "free": True},
        "toilet": {"available": True, "western": True},
        "stairs": 1,
        "barrierFree": 4,
        "dogRun": {"available": True, "free": True, "detail": "砂地エリアと芝生エリアの2区画。犬種制限なし。無料。", "separated": False},
        "admission": {"free": True, "fee": ""},
        "visited": False,
        "remarks": "砂地と芝生の2つのドッグランエリアがある海岸沿いの公園。屋根付き休憩スペースあり。駐車場無料。",
        "imageUrl": "",
        "officialUrl": "https://www.city.wakayama.wakayama.jp/",
        "aliases": [],
        "tags": []
    },
    {
        "id": "kinokawa-daiichi-ryokuchi",
        "name": "紀の川第1緑地",
        "address": "和歌山県和歌山市湊",
        "lat": 34.2441,
        "lng": 135.1892,
        "category": "park",
        "dogSize": {"small": True, "large": True},
        "parking": {"available": True, "free": True},
        "toilet": {"available": True, "western": False},
        "stairs": 1,
        "barrierFree": 4,
        "dogRun": {"available": True, "free": True, "detail": "大型・中型犬用と小型犬用の2エリアに分離。無料。24時間利用可。", "separated": True},
        "admission": {"free": True, "fee": ""},
        "visited": False,
        "remarks": "紀の川沿いの河川敷にある無料ドッグラン。24時間365日利用可。大中型犬・小型犬の2エリア分離。駐車場約20台・無料。問い合わせ：073-435-1076（公園緑地課）。",
        "imageUrl": "",
        "officialUrl": "https://www.city.wakayama.wakayama.jp/shisetsu/kouen_sp_shisetsu/1006085/1010420.html",
        "aliases": ["紀の川第一緑地"],
        "tags": []
    },
    {
        "id": "bansho-yama-park",
        "name": "番所山公園",
        "address": "和歌山県西牟婁郡白浜町3601-1",
        "lat": 33.6774,
        "lng": 135.3487,
        "category": "walk",
        "dogSize": {"small": True, "large": True},
        "parking": {"available": True, "free": True},
        "toilet": {"available": True, "western": True},
        "stairs": 2,
        "barrierFree": 2,
        "dogRun": {"available": False, "free": False, "detail": "", "separated": False},
        "admission": {"free": True, "fee": ""},
        "visited": False,
        "remarks": "国立自然公園に指定された白浜の岬にある公園。円月島など南紀白浜の絶景が眺望できる。犬連れで散策可。駐車場無料。",
        "imageUrl": "",
        "officialUrl": "https://www.biwako-visitors.jp/",
        "aliases": [],
        "tags": []
    },
    {
        "id": "shirasaki-kaiyo-park",
        "name": "白崎海洋公園",
        "address": "和歌山県日高郡由良町大引960-1",
        "lat": 33.9671,
        "lng": 135.1197,
        "category": "walk",
        "dogSize": {"small": True, "large": True},
        "parking": {"available": True, "free": True},
        "toilet": {"available": True, "western": True},
        "stairs": 2,
        "barrierFree": 2,
        "dogRun": {"available": False, "free": False, "detail": "", "separated": False},
        "admission": {"free": True, "fee": ""},
        "visited": False,
        "remarks": "「日本のエーゲ海」と称される白い石灰岩の海岸公園。国定公園内に位置し、奇岩と青い海のコントラストが絶景。犬連れ散策可。駐車場無料。",
        "imageUrl": "",
        "officialUrl": "https://shirasaki-resort.com/",
        "aliases": ["白崎海岸"],
        "tags": []
    }
]

spots.extend(new_spots)

with open('data/spots.json', 'w', encoding='utf-8') as f:
    json.dump(spots, f, ensure_ascii=False, indent=2)

print(f"追加完了: {len(new_spots)}件追加、全{len(spots)}件")
wakayama = [s for s in spots if "和歌山" in s.get("address", "")]
print(f"和歌山: {len(wakayama)}件")
for s in wakayama:
    print(f"  - {s['name']}")

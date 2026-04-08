import json

with open('data/spots.json', 'r', encoding='utf-8') as f:
    spots = json.load(f)

existing_ids = {s['id'] for s in spots}

new_spots = [
    {
        "id": "biwako-umenosato-dogrun",
        "name": "びわこ梅の郷ドッグラン",
        "address": "滋賀県野洲市吉川2425",
        "lat": 35.129267,
        "lng": 135.993438,
        "parking": {"available": True, "free": True},
        "toilet": {"available": True, "western": False},
        "dogRun": {
            "available": True,
            "free": False,
            "separated": True,
            "detail": "大型犬エリア・小中型犬エリアなど最大4区画。天然芝約1,800坪。1頭500円/日。スタンプカード10回で1回無料。"
        },
        "admission": {"free": True, "fee": ""},
        "visited": False,
        "tags": [],
        "aliases": ["梅の郷ドッグラン"],
        "remarks": "琵琶湖近くの広大なドッグラン。梅の木が多数あり梅狩りも可能（300円/kg）。営業時間9:00-17:00、定休日は木曜日。公式サイトはFacebookのみ。",
        "officialUrl": "https://www.facebook.com/biwakoumenosatodogrun/"
    },
    {
        "id": "takama-mizube-park",
        "name": "高間みずべ公園",
        "address": "滋賀県甲賀市甲賀町油日2216",
        "lat": 34.871759,
        "lng": 136.255571,
        "parking": {"available": True, "free": True},
        "toilet": {"available": True, "western": False},
        "dogRun": {
            "available": False,
            "free": False,
            "separated": False,
            "detail": ""
        },
        "admission": {"free": True, "fee": ""},
        "visited": False,
        "tags": ["water"],
        "aliases": [],
        "remarks": "油日岳山麓の清流沿いの公園。川遊びやバーベキューが楽しめる。犬連れ散策可だが、混雑時など場合によりお断りの場合あり（事前確認推奨）。開園4月-11月末。",
        "officialUrl": "https://www.city.koka.lg.jp/12769.htm"
    },
    {
        "id": "enmei-park",
        "name": "延命公園",
        "address": "滋賀県東近江市八日市松尾町",
        "lat": 35.112500,
        "lng": 136.200833,
        "parking": {"available": True, "free": True},
        "toilet": {"available": True, "western": False},
        "dogRun": {
            "available": False,
            "free": False,
            "separated": False,
            "detail": ""
        },
        "admission": {"free": True, "fee": ""},
        "visited": False,
        "tags": ["sakura"],
        "aliases": [],
        "remarks": "延命山の自然を活かした公園。ソメイヨシノ約1,000本の桜の名所。アップダウンがあり犬の散歩に最適。駐車場が少ないため桜シーズンは要注意。トイレは和式の可能性あり（要確認）。",
        "officialUrl": "https://www.city.higashiomi.shiga.jp/0000001150.html"
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

# 既存の鮎河の千本桜にwaterタグ追加
for s in spots:
    if s['id'] == 'ayukawa-senbonzakura':
        if 'water' not in s.get('tags', []):
            s.setdefault('tags', []).append('water')
            print(f"  - 鮎河の千本桜: waterタグ追加")
        break

with open('data/spots.json', 'w', encoding='utf-8') as f:
    json.dump(spots, f, ensure_ascii=False, indent=2)

print(f"\n{added}件追加 (合計{len(spots)}件)")

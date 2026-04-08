import json

with open('data/spots.json', 'r', encoding='utf-8') as f:
    spots = json.load(f)

existing_ids = {s['id'] for s in spots}

new_spots = [
    {
        "id": "seseragi-no-sato-koura",
        "name": "道の駅 せせらぎの里こうら",
        "address": "滋賀県犬上郡甲良町金屋1549-4",
        "lat": 35.201897,
        "lng": 136.275326,
        "parking": {"available": True, "free": True},
        "toilet": {"available": True, "western": True},
        "dogRun": {
            "available": True,
            "free": True,
            "separated": True,
            "detail": "小型犬エリア（10kg以下）・中大型犬エリア（10kg超）・貸切エリアの3区画。天然芝。利用時間9:30-17:00（11-2月は16:00まで）。"
        },
        "admission": {"free": True, "fee": ""},
        "visited": False,
        "tags": [],
        "aliases": ["せせらぎの里こうら", "せせらぎの里"],
        "remarks": "わんこ用石窯焼きピザを販売しており犬連れに人気の道の駅。地元野菜の直売所・レストランも併設。定休日は第2月曜日。犬はリード着用で散策可。",
        "officialUrl": "https://m-koura.jp/"
    },
    {
        "id": "shirahige-jinja",
        "name": "白鬚神社",
        "address": "滋賀県高島市鵜川215",
        "lat": 35.274634,
        "lng": 136.011314,
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
        "tags": [],
        "aliases": ["白髭神社"],
        "remarks": "琵琶湖に浮かぶ大鳥居が絶景の近江最古の神社。犬はリード着用で境内散策可（建物内は不可）。国道161号沿い。トイレは和式のみの情報あり。",
        "officialUrl": "http://shirahigejinja.com/"
    },
    {
        "id": "mitsui-outlet-shiga-ryuo",
        "name": "三井アウトレットパーク 滋賀竜王",
        "address": "滋賀県蒲生郡竜王町大字薬師1178-694",
        "lat": 35.058692,
        "lng": 136.099555,
        "parking": {"available": True, "free": True},
        "toilet": {"available": True, "western": True},
        "dogRun": {
            "available": True,
            "free": False,
            "separated": True,
            "detail": "パインズドッグラン。小型犬（約10kg未満）・中大型犬（約10kg以上）の2区画。1頭1,000円/日（会員900円）。ワクチン証明書必要。"
        },
        "admission": {"free": True, "fee": ""},
        "visited": False,
        "tags": [],
        "aliases": ["三井アウトレット滋賀竜王", "アウトレット竜王", "三井アウトレット竜王"],
        "remarks": "日本最大級のアウトレットモール。館内はペットカート・スリング等でのキャリー必須（屋外はリードOK）。ペットカート貸出2時間1,000円。一時預かりサービスもあり。",
        "officialUrl": "https://mitsui-shopping-park.com/mop/shiga/"
    },
    {
        "id": "kusatsugawa-atochi-park",
        "name": "草津川跡地公園 ai彩ひろば",
        "address": "滋賀県草津市大路2丁目1-35",
        "lat": 35.016389,
        "lng": 135.961667,
        "parking": {"available": True, "free": True},
        "toilet": {"available": True, "western": True},
        "dogRun": {
            "available": True,
            "free": False,
            "separated": False,
            "detail": "1人300円/時間。貸切3,000円/時間（要予約）。エリア分離の詳細は要確認。"
        },
        "admission": {"free": True, "fee": ""},
        "visited": False,
        "tags": [],
        "aliases": ["草津川跡地公園", "ai彩ひろば"],
        "remarks": "旧草津川の跡地を整備した公園内のドッグラン。JR草津駅から徒歩圏内。併設カフェのテラス席は犬同伴OK。犬はリード着用で公園内散策可。",
        "officialUrl": "https://www.kusatsugawaatochi-park.com/"
    },
    {
        "id": "miidera",
        "name": "三井寺（園城寺）",
        "address": "滋賀県大津市園城寺町246",
        "lat": 35.012334,
        "lng": 135.852242,
        "parking": {"available": True, "free": False},
        "toilet": {"available": True, "western": True},
        "dogRun": {
            "available": False,
            "free": False,
            "separated": False,
            "detail": ""
        },
        "admission": {"free": False, "fee": "大人800円、中高生500円、小学生300円"},
        "visited": False,
        "tags": ["sakura", "koyo"],
        "aliases": ["三井寺", "園城寺"],
        "remarks": "天台寺門宗の総本山。境内約12万平方メートルの広大な散策が楽しめる。犬はリード着用で境内散策可（堂内・建物内は不可）。拝観時間9:00-16:30。駐車場は近隣有料駐車場利用（500円程度）。",
        "officialUrl": "https://miidera1200.jp/"
    },
    {
        "id": "hikone-castle",
        "name": "彦根城",
        "address": "滋賀県彦根市金亀町1-1",
        "lat": 35.275366,
        "lng": 136.251638,
        "parking": {"available": True, "free": False},
        "toilet": {"available": True, "western": True},
        "dogRun": {
            "available": False,
            "free": False,
            "separated": False,
            "detail": ""
        },
        "admission": {"free": False, "fee": "大人1,000円、小中学生300円"},
        "visited": False,
        "tags": ["sakura", "koyo"],
        "aliases": ["彦根城跡"],
        "remarks": "国宝天守を持つ名城。犬はリード着用で城内（屋外）散策可。天守・各建物内への入場は不可。ひこにゃんに会えるスポット。桜シーズンは大変混雑。観光駐車場1日1,000円。",
        "officialUrl": "https://hikonecastle.com/"
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

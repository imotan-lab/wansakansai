"""滋賀ブログ記事用の画像処理スクリプト
顔ぼかし + Webサイズへのリサイズ
"""
import cv2
import numpy as np
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from blur_faces import detect_faces_yunet, blur_face_ellipse

SRC_BASE = r"C:\Users\oh_so\Downloads"
DST_DIR = r"images/blog/shiga-biwako-2days"
WEB_WIDTH = 1200

# (フォルダ名, 元ファイル番号, 出力ファイル名)
photos = [
    # R cafe
    ("Rカフェ", "03", "rcafe-01-signboard.jpg"),
    ("Rカフェ", "12", "rcafe-02-exterior.jpg"),
    ("Rカフェ", "08", "rcafe-03-terrace.jpg"),
    ("Rカフェ", "06", "rcafe-04-lunch.jpg"),
    ("Rカフェ", "07", "rcafe-05-dogmenu.jpg"),
    ("Rカフェ", "01", "rcafe-06-kotsubu.jpg"),
    ("Rカフェ", "14", "rcafe-07-rain.jpg"),
    # かばたリゾート
    ("カバタリゾート", "01", "kabata-01-reception.jpg"),
    ("カバタリゾート", "07", "kabata-02-rules.jpg"),
    ("カバタリゾート", "08", "kabata-03-indoor-dogrun.jpg"),
    ("カバタリゾート", "05", "kabata-04-pool-entrance.jpg"),
    # ホリデーアフタヌーン
    ("ホリデーアフタヌーン", "02", "horiaf-01-signboard.jpg"),
    ("ホリデーアフタヌーン", "14", "horiaf-02-dogrun.jpg"),
    ("ホリデーアフタヌーン", "13", "horiaf-03-cottage-gate.jpg"),
    ("ホリデーアフタヌーン", "32", "horiaf-04-cottages.jpg"),
    ("ホリデーアフタヌーン", "26", "horiaf-05-onsen.jpg"),
    ("ホリデーアフタヌーン", "29", "horiaf-06-living.jpg"),
    ("ホリデーアフタヌーン", "30", "horiaf-07-bedroom.jpg"),
    ("ホリデーアフタヌーン", "36", "horiaf-08-cafe.jpg"),
    ("ホリデーアフタヌーン", "37", "horiaf-09-bread.jpg"),
    # アグリパーク竜王
    ("道の駅　竜王", "08", "aguri-01-flowers.jpg"),
    ("道の駅　竜王", "09", "aguri-02-dogrun-sign.jpg"),
    ("道の駅　竜王", "14", "aguri-03-tulip.jpg"),
    ("道の駅　竜王", "04", "aguri-04-flowers2.jpg"),
    # 高野いちご園
    ("高野いちご園", "02", "takano-01-signboard.jpg"),
    ("高野いちご園", "12", "takano-02-exterior.jpg"),
    ("高野いちご園", "07", "takano-03-house.jpg"),
    ("高野いちご園", "13", "takano-04-cart.jpg"),
]

os.makedirs(DST_DIR, exist_ok=True)

for folder, num, out_name in photos:
    src = os.path.join(SRC_BASE, folder, f"{num}.jpg")
    dst = os.path.join(DST_DIR, out_name)

    if not os.path.exists(src):
        print(f"SKIP: {src} not found")
        continue

    # 日本語パス対応
    with open(src, 'rb') as f:
        data = np.frombuffer(f.read(), dtype=np.uint8)
    img = cv2.imdecode(data, cv2.IMREAD_COLOR)
    if img is None:
        print(f"SKIP: cannot decode {src}")
        continue

    # 顔検出
    faces = detect_faces_yunet(img, score_threshold=0.5)
    if faces:
        for x, y, w, h, score in faces:
            img = blur_face_ellipse(img, x, y, w, h)
        print(f"{out_name}: {len(faces)} faces blurred")
    else:
        print(f"{out_name}: no faces")

    # リサイズ
    h, w = img.shape[:2]
    new_w = WEB_WIDTH
    new_h = int(h * new_w / w)
    resized = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
    cv2.imwrite(dst, resized, [cv2.IMWRITE_JPEG_QUALITY, 82])

print(f"\nDone: {len(photos)} images processed to {DST_DIR}")

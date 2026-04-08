"""ブログ用画像の一括処理スクリプト
顔ぼかし + Webサイズへのリサイズ
"""
import cv2
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from blur_faces import detect_faces_yunet, blur_face_ellipse

SRC_DIR = r"C:\Users\oh_so\今電 Dropbox\今電　今尾笙夢\わんさかんさい訪問写真\近つ飛鳥"
DST_DIR = r"images/blog/chikatsu-asuka-sakura"
WEB_WIDTH = 1200

# 使う写真番号とぼかし要否
photos = [
    # 駐車場・入口
    (1, False), (4, False), (6, False),
    # グレーチング
    (13, False),
    # 大階段
    (9, False), (10, False), (11, False),
    # スロープ
    (60, False),
    # 丘への道
    (8, False), (14, True), (15, False), (16, False),
    # 桜の遊歩道・こつぶ
    (17, False), (18, False), (20, False), (21, False), (24, False),
    # マムシ
    (26, False),
    # 桜並木
    (28, False), (29, False),
    # 管理棟エリア
    (33, False), (34, False), (38, False),
    # トイレ・自販機
    (42, False), (40, False),
    # 平成の通り抜け
    (49, False), (44, False), (45, True), (46, True), (48, True),
    # 比較
    (63, False), (73, True),
    # 丘側駐車場
    (53, False), (55, False),
    # 帰り
    (61, False), (62, False),
    # 前回: 展望台
    (64, False), (70, False), (71, False), (72, False),
]

os.makedirs(DST_DIR, exist_ok=True)

for num, needs_blur in photos:
    src = os.path.join(SRC_DIR, f"{num:02d}.jpg")
    dst = os.path.join(DST_DIR, f"{num:02d}.jpg")

    if not os.path.exists(src):
        print(f"SKIP: {src} not found")
        continue

    # OpenCVは日本語パスを読めないのでnumpyで読む
    import numpy as np
    with open(src, 'rb') as f:
        data = np.frombuffer(f.read(), dtype=np.uint8)
    img = cv2.imdecode(data, cv2.IMREAD_COLOR)
    if img is None:
        print(f"SKIP: cannot decode {src}")
        continue

    if needs_blur:
        faces = detect_faces_yunet(img, score_threshold=0.3)
        for x, y, w, h, score in faces:
            img = blur_face_ellipse(img, x, y, w, h)
        print(f"{num:02d}.jpg: {len(faces)} faces blurred")
    else:
        print(f"{num:02d}.jpg: no blur needed")

    # リサイズ
    oh, ow = img.shape[:2]
    new_w = WEB_WIDTH
    new_h = int(oh * new_w / ow)
    resized = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
    cv2.imwrite(dst, resized, [cv2.IMWRITE_JPEG_QUALITY, 82])

print(f"\nDone: {len(photos)} images processed to {DST_DIR}")

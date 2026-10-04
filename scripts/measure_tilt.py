"""写真の傾きを測る（掲載する写真は毎回これで確かめる。CLAUDE.md「傾いた写真は回転して水平に直す」）。

使い方:
    python scripts/measure_tilt.py <写真> "x0,x1,y0,y1" ["x0,x1,y0,y1" ...]
    python scripts/measure_tilt.py <写真> --rotate 0.65 "x0,x1,y0,y1"    # 回したあとに測り直す

範囲は割合（0〜1）。写真の中で「本来は水平な、はっきりした横の境目」を囲む帯を指定する
（建物の軒・窓の上端・石垣の縁・欄干・看板の縁など）。列ごとに境目の高さを拾って直線を当てはめる。

出力の角度: 正 = 右下がり、負 = 右上がり。直すときは PIL の Image.rotate(角度) にこの値をそのまま渡す。
- 左右の別々の範囲で同じ向き・近い値が出たら信用してよい（例: 左の軒 -1.16 と右の軒 -1.55）
- 「ばらつき」が数px を超える範囲は境目を拾えていないので使わない
- 0.5°未満は見て分からないので直さなくてよい
- 回したら --rotate を付けて測り直し、±0.3°以内になったことを確かめる。回してできた黒い縁は内接する4:3で切り落とす

2026-10-04 に作った。HoughLinesP（直線検出）は高解像度の写真で線を拾えず、当てにならなかったため、この方法にした。
"""
import sys
import cv2
import numpy as np
from PIL import Image, ImageOps


def edge_angle(img, x0, x1, y0, y1):
    H, W = img.shape[:2]
    g = cv2.GaussianBlur(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32), (0, 0), 2)
    gy = np.abs(cv2.Sobel(g, cv2.CV_32F, 0, 1, ksize=5))
    ya, yb = int(H * y0), int(H * y1)
    xs, ys = [], []
    for x in np.linspace(W * x0, W * x1, 60).astype(int):
        col = gy[ya:yb, max(0, x - 3):x + 4].mean(axis=1)
        if col.size == 0 or col.max() < 5:
            continue
        xs.append(x); ys.append(ya + int(np.argmax(col)))
    if len(xs) < 5:
        return None, len(xs), None
    xs, ys = np.array(xs, float), np.array(ys, float)
    for _ in range(3):
        k, b = np.polyfit(xs, ys, 1)
        r = np.abs(ys - (k * xs + b))
        keep = r < max(3.0, np.percentile(r, 70))
        xs, ys = xs[keep], ys[keep]
    k, b = np.polyfit(xs, ys, 1)
    return float(np.degrees(np.arctan(k))), len(xs), float(np.std(ys - (k * xs + b)))


def main():
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except Exception:
            pass
    args = sys.argv[1:]
    if len(args) < 2:
        print(__doc__)
        return 1
    path, rest = args[0], args[1:]
    rot = 0.0
    if rest and rest[0] == "--rotate":
        rot = float(rest[1]); rest = rest[2:]
    im = ImageOps.exif_transpose(Image.open(path)).convert("RGB")
    if rot:
        im = im.rotate(rot, resample=Image.BICUBIC)
    img = cv2.cvtColor(np.array(im), cv2.COLOR_RGB2BGR)
    for spec in rest:
        x0, x1, y0, y1 = [float(v) for v in spec.split(",")]
        a, cnt, sd = edge_angle(img, x0, x1, y0, y1)
        if a is None:
            print(f"範囲 {spec}: 境目を拾えず（{cnt}点）")
        else:
            print(f"範囲 {spec}: {a:+.2f}°（{cnt}点・ばらつき{sd:.1f}px）" + ("  ←ばらつき大・使わない" if sd > 4 else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())

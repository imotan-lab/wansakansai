"""顔ぼかし（フィルタ適用）＋Webリサイズを一括で行う。"""
import sys
import cv2
import numpy as np
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import blur_faces as bf

bf.MODEL_PATH = r"C:\Users\imao_\.claude\face_detection_yunet.onnx"


def imread_u(p: str):
    return cv2.imdecode(np.fromfile(p, dtype=np.uint8), cv2.IMREAD_COLOR)


def imwrite_u(p: str, img, params=None) -> bool:
    ret, buf = cv2.imencode(Path(p).suffix, img, params or [])
    if ret:
        buf.tofile(p)
    return bool(ret)


def process(input_path: str, output_path: str, keep: str | list = "all",
            score_threshold: float = 0.3, resize_w: int = 1200, quality: int = 85) -> int:
    """keep = 'all' | 'none' | [indices]"""
    img = imread_u(input_path)
    if img is None:
        print(f"ERROR: cannot read {input_path}")
        return -1

    if keep == "none":
        faces = []
    else:
        detected = bf.detect_faces_yunet(img, score_threshold=score_threshold)
        if keep == "all":
            faces = detected
        else:
            faces = [detected[i] for i in keep if 0 <= i < len(detected)]

    for (x, y, w, h, score) in faces:
        img = bf.blur_face_ellipse(img, x, y, w, h)

    # リサイズ（横幅を resize_w に）
    h, w = img.shape[:2]
    if w > resize_w:
        ratio = resize_w / w
        img = cv2.resize(img, (resize_w, int(h * ratio)), interpolation=cv2.INTER_AREA)

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    imwrite_u(output_path, img, [cv2.IMWRITE_JPEG_QUALITY, quality])
    print(f"{Path(input_path).name} -> {Path(output_path).name}: {len(faces)} blurred")
    return len(faces)


if __name__ == "__main__":
    SRC = r"C:\Users\imao_\今電 Dropbox\今電　今尾笙夢\わんさかんさい訪問写真\海フレ"
    DST = Path(__file__).resolve().parent.parent / "images" / "spots" / "umi-fureai-hiroba"

    # 各写真の処理仕様（elm: (入力ファイル名末尾時刻, 出力番号, keep指定)）
    jobs = [
        ("14 43 08", 1, "none"),        # 掲示板：誤検出2件のみ、ぼかし不要
        ("14 44 20", 2, [0]),            # 小型犬入口：#1のみ実人物
        ("14 46 57", 3, "all"),          # ドッグラン賑わい：全15件実人物
        ("15 21 40", 4, [0]),            # シェルター：#1のみ実人物
        ("15 22 29", 5, "all"),          # 広場全景：全10件実人物
        ("15 26 39", 6, "all"),          # 管理事務所：全3件（低スコアだが念のため）
    ]

    for suffix, num, keep in jobs:
        src = f"{SRC}\\写真 2026-04-19 {suffix}.jpg"
        dst = str(DST / f"photo_{num}.jpg")
        process(src, dst, keep=keep)

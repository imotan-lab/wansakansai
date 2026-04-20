"""顔検出して検出結果を画像に描画（目視判別用）"""
import sys
import cv2
import numpy as np
from pathlib import Path

# blur_faces.py を取り込む
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import blur_faces as bf

# モデルはASCIIパスに配置（OpenCVのONNXローダが日本語パスを読めない対策）
bf.MODEL_PATH = r"C:\Users\imao_\.claude\face_detection_yunet.onnx"


def imread_unicode(path: str):
    """日本語パス対応のimread"""
    return cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_COLOR)


def imwrite_unicode(path: str, img, params=None):
    """日本語パス対応のimwrite"""
    ext = Path(path).suffix
    ret, buf = cv2.imencode(ext, img, params or [])
    if ret:
        buf.tofile(path)
    return ret


def visualize(input_path: str, output_path: str, score_threshold: float = 0.3):
    img = imread_unicode(input_path)
    if img is None:
        print(f"ERROR: cannot read {input_path}")
        return []
    faces = bf.detect_faces_yunet(img, score_threshold=score_threshold)
    print(f"[{Path(input_path).name}] detected: {len(faces)} faces")
    vis = img.copy()
    for i, (x, y, w, h, score) in enumerate(faces):
        cv2.rectangle(vis, (x, y), (x + w, y + h), (0, 0, 255), 3)
        label = f"#{i+1} s={score:.2f}"
        cv2.putText(vis, label, (x, max(0, y - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
        print(f"  #{i+1}: ({x},{y}) {w}x{h} score={score:.2f}")
    imwrite_unicode(output_path, vis, [cv2.IMWRITE_JPEG_QUALITY, 85])
    return faces


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python detect_and_visualize.py <input> <output> [score_threshold]")
        sys.exit(1)
    th = float(sys.argv[3]) if len(sys.argv) > 3 else 0.3
    visualize(sys.argv[1], sys.argv[2], th)

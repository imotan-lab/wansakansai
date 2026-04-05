"""顔検出＆ぼかし処理スクリプト（YuNet DNN版）
使い方: python blur_faces.py <入力画像> <出力画像>

YuNetで顔をピンポイント検出し、顔部分だけを自然にぼかす。
"""
import sys
import cv2
import numpy as np
import os

MODEL_PATH = os.path.join('C:/Users/oh_so', 'face_detection_yunet.onnx')


def detect_faces_yunet(img, score_threshold=0.5):
    """YuNetで顔検出。複数スケールで検出して小さい顔も拾う"""
    h, w = img.shape[:2]
    all_faces = []

    # 複数スケールで検出（元サイズ + 拡大）
    scales = [1.0]
    if max(h, w) > 2000:
        scales.append(2000 / max(h, w))  # 縮小版
    if max(h, w) < 3000:
        scales.append(min(2.0, 4000 / max(h, w)))  # 拡大版

    for scale in scales:
        sh, sw = int(h * scale), int(w * scale)
        if sh < 100 or sw < 100:
            continue
        resized = cv2.resize(img, (sw, sh)) if scale != 1.0 else img

        detector = cv2.FaceDetectorYN.create(MODEL_PATH, "", (sw, sh),
                                              score_threshold=score_threshold,
                                              nms_threshold=0.3,
                                              top_k=50)
        _, faces = detector.detect(resized)

        if faces is not None:
            for face in faces:
                # 元の座標に戻す
                x, y, fw, fh = face[0]/scale, face[1]/scale, face[2]/scale, face[3]/scale
                score = face[-1]
                all_faces.append((int(x), int(y), int(fw), int(fh), score))

    # 重複除去（IoU）
    unique = []
    for face in sorted(all_faces, key=lambda f: -f[4]):  # スコア順
        is_dup = False
        for uf in unique:
            iou = calc_iou(face[:4], uf[:4])
            if iou > 0.3:
                is_dup = True
                break
        if not is_dup:
            unique.append(face)

    return unique


def calc_iou(box1, box2):
    x1 = max(box1[0], box2[0])
    y1 = max(box1[1], box2[1])
    x2 = min(box1[0] + box1[2], box2[0] + box2[2])
    y2 = min(box1[1] + box1[3], box2[1] + box2[3])
    inter = max(0, x2 - x1) * max(0, y2 - y1)
    area1 = box1[2] * box1[3]
    area2 = box2[2] * box2[3]
    union = area1 + area2 - inter
    return inter / union if union > 0 else 0


def blur_face_ellipse(img, x, y, w, h):
    """楕円形で顔だけ自然にぼかす"""
    # 顔の中心
    cx = x + w // 2
    cy = y + h // 2
    # 少しだけマージン（顔の輪郭をカバー）
    rw = int(w * 0.6)
    rh = int(h * 0.65)

    # マスク作成
    mask = np.zeros(img.shape[:2], dtype=np.uint8)
    cv2.ellipse(mask, (cx, cy), (rw, rh), 0, 0, 360, 255, -1)

    # ぼかし強度を顔サイズに合わせる
    ksize = max(31, (max(w, h) // 2) * 2 + 1)
    blurred = cv2.GaussianBlur(img, (ksize, ksize), 20)

    # マスクでブレンド（境界を自然に）
    mask_blur = cv2.GaussianBlur(mask, (21, 21), 10)
    mask_3ch = cv2.merge([mask_blur, mask_blur, mask_blur]) / 255.0
    img = (img * (1 - mask_3ch) + blurred * mask_3ch).astype(np.uint8)

    return img


def blur_faces(input_path, output_path):
    img = cv2.imread(input_path)
    if img is None:
        print(f"ERROR: cannot read {input_path}")
        return False

    faces = detect_faces_yunet(img, score_threshold=0.3)
    print(f"detected: {len(faces)} faces")

    for i, (x, y, w, h, score) in enumerate(faces):
        print(f"  face {i+1}: ({x},{y}) {w}x{h} score={score:.2f}")
        img = blur_face_ellipse(img, x, y, w, h)

    cv2.imwrite(output_path, img, [cv2.IMWRITE_JPEG_QUALITY, 92])
    print(f"saved: {output_path}")
    return True


if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("usage: python blur_faces.py <input> <output>")
        sys.exit(1)
    success = blur_faces(sys.argv[1], sys.argv[2])
    sys.exit(0 if success else 1)
